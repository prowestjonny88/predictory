"""
Waste risk alert logic — Task 8
detect_waste_risk(target_date, db) -> list[WasteAlert]
"""
from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session

from db.models import SalesFact, WasteLog, PrepPlanLine, PrepPlan, Outlet, SKU

PREP_OVER_FORECAST_THRESHOLD = 0.15  # alert if prep > forecast * (1 + 0.15)
WASTE_RATE_3D_THRESHOLD = 0.10       # alert if 3-day waste rate > 10%
CONSECUTIVE_DECLINE_DAYS = 3

DAYPARTS = ["morning", "midday", "evening"]


@dataclass
class WasteAlert:
    outlet_id: int
    outlet_name: str
    sku_id: int
    sku_name: str
    daypart: str
    risk_level: str  # high / medium / low
    triggers: list[str]
    reason: str
    waste_rate: float = 0.0
    excess_prep_units: float = 0.0


def _get_daypart_sales(db: Session, outlet_id: int, sku_id: int, daypart: str, days: int, before_date: date) -> list[int]:
    start = before_date - timedelta(days=days)
    rows = db.query(SalesFact).filter(
        SalesFact.outlet_id == outlet_id,
        SalesFact.sku_id == sku_id,
        SalesFact.daypart == daypart,
        SalesFact.sale_date >= start,
        SalesFact.sale_date < before_date,
    ).order_by(SalesFact.sale_date.asc()).all()
    return [r.units_sold for r in rows]


def _get_waste_rate_3d(db: Session, outlet_id: int, sku_id: int, before_date: date) -> float:
    start = before_date - timedelta(days=3)
    waste_rows = db.query(WasteLog).filter(
        WasteLog.outlet_id == outlet_id,
        WasteLog.sku_id == sku_id,
        WasteLog.waste_date >= start,
        WasteLog.waste_date < before_date,
    ).all()
    total_wasted = sum(w.units_wasted for w in waste_rows)

    sales_rows = db.query(SalesFact).filter(
        SalesFact.outlet_id == outlet_id,
        SalesFact.sku_id == sku_id,
        SalesFact.sale_date >= start,
        SalesFact.sale_date < before_date,
    ).all()
    total_sold = sum(s.units_sold for s in sales_rows)

    denominator = total_sold + total_wasted
    return total_wasted / denominator if denominator > 0 else 0.0


def detect_waste_risk(target_date: date, db: Session) -> list[WasteAlert]:
    outlets = db.query(Outlet).filter(Outlet.is_active == True).all()
    skus = db.query(SKU).filter(SKU.is_active == True).all()

    # Get latest prep plan for target_date
    prep_plan = (
        db.query(PrepPlan)
        .filter(PrepPlan.plan_date == target_date)
        .order_by(PrepPlan.created_at.desc())
        .first()
    )

    # Build prep dict: {(outlet_id, sku_id, daypart): recommended_units}
    prep_map: dict[tuple, int] = {}
    if prep_plan:
        for line in prep_plan.lines:
            qty = line.edited_units if line.edited_units is not None else line.recommended_units
            prep_map[(line.outlet_id, line.sku_id, line.daypart)] = qty

    alerts: list[WasteAlert] = []

    for outlet in outlets:
        for sku in skus:
            for dp in DAYPARTS:
                triggers: list[str] = []
                waste_rate = _get_waste_rate_3d(db, outlet.id, sku.id, target_date)
                sales_series = _get_daypart_sales(db, outlet.id, sku.id, dp, 7, target_date)

                # Trigger 1: prep exceeds forecast by >15%
                prep_qty = prep_map.get((outlet.id, sku.id, dp), 0)
                avg_sales = sum(sales_series) / len(sales_series) if sales_series else 0
                excess = 0.0
                if avg_sales > 0 and prep_qty > avg_sales * (1 + PREP_OVER_FORECAST_THRESHOLD):
                    excess = prep_qty - avg_sales
                    triggers.append(f"Prep ({prep_qty}) exceeds expected demand ({avg_sales:.0f}) by >{PREP_OVER_FORECAST_THRESHOLD:.0%}")

                # Trigger 2: 3-day waste rate > 10%
                if waste_rate > WASTE_RATE_3D_THRESHOLD:
                    triggers.append(f"3-day waste rate {waste_rate:.1%} > 10%")

                # Trigger 3: evening daypart declined 3+ consecutive days
                if dp == "evening" and len(sales_series) >= CONSECUTIVE_DECLINE_DAYS:
                    recent = sales_series[-CONSECUTIVE_DECLINE_DAYS:]
                    if all(recent[i] >= recent[i + 1] for i in range(len(recent) - 1)):
                        triggers.append(f"Evening sales declining for {CONSECUTIVE_DECLINE_DAYS}+ consecutive days")

                if not triggers:
                    continue

                risk_level = "high" if len(triggers) >= 2 else "medium"
                reason = "; ".join(triggers)

                alerts.append(WasteAlert(
                    outlet_id=outlet.id,
                    outlet_name=outlet.name,
                    sku_id=sku.id,
                    sku_name=sku.name,
                    daypart=dp,
                    risk_level=risk_level,
                    triggers=triggers,
                    reason=reason,
                    waste_rate=round(waste_rate, 3),
                    excess_prep_units=round(excess, 1),
                ))

    # Sort: high risk first
    alerts.sort(key=lambda a: (0 if a.risk_level == "high" else 1 if a.risk_level == "medium" else 2))
    return alerts
