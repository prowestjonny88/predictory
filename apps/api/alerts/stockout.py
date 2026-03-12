"""
Stockout risk alert logic — Task 9
detect_stockout_risk(target_date, db) -> list[StockoutAlert]
"""
from datetime import date, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session

from db.models import (
    SalesFact, InventorySnapshot, PrepPlanLine, PrepPlan,
    Ingredient, RecipeBOM, SKU, Outlet
)
from forecasting.engine import forecast_demand

BESTSELLER_COVERAGE_THRESHOLD = 0.90  # 90%
STANDARD_COVERAGE_THRESHOLD   = 0.80  # 80%

DAYPARTS = ["morning", "midday", "evening"]


@dataclass
class StockoutAlert:
    outlet_id: int
    outlet_name: str
    sku_id: int
    sku_name: str
    affected_daypart: str
    risk_level: str   # high / medium / low
    shortage_qty: float
    reason: str
    coverage_pct: float = 0.0


def _get_stock(db: Session, outlet_id: int, sku_id: int) -> int:
    snap = (
        db.query(InventorySnapshot)
        .filter(
            InventorySnapshot.outlet_id == outlet_id,
            InventorySnapshot.sku_id == sku_id,
        )
        .order_by(InventorySnapshot.snapshot_date.desc())
        .first()
    )
    return snap.units_on_hand if snap else 0


def _get_recent_daypart_peak(
    db: Session,
    outlet_id: int,
    sku_id: int,
    daypart: str,
    target_date: date,
    lookback_days: int = 7,
) -> int:
    start = target_date - timedelta(days=lookback_days)
    rows = (
        db.query(SalesFact)
        .filter(
            SalesFact.outlet_id == outlet_id,
            SalesFact.sku_id == sku_id,
            SalesFact.daypart == daypart,
            SalesFact.sale_date >= start,
            SalesFact.sale_date < target_date,
        )
        .all()
    )
    return max((row.units_sold for row in rows), default=0)


def _get_ingredient_coverage(db: Session, target_date: date) -> float:
    """Returns fraction of total ingredient need that is covered by current stock."""
    # Get latest prep plan
    prep_plan = (
        db.query(PrepPlan)
        .filter(PrepPlan.plan_date == target_date)
        .order_by(PrepPlan.created_at.desc())
        .first()
    )
    if not prep_plan:
        return 1.0  # assume ok if no plan

    sku_total: dict[int, float] = {}
    for line in prep_plan.lines:
        qty = line.edited_units if line.edited_units is not None else line.recommended_units
        sku_total[line.sku_id] = sku_total.get(line.sku_id, 0) + qty

    total_need: dict[int, float] = {}
    bom_rows = db.query(RecipeBOM).all()
    for bom in bom_rows:
        prep = sku_total.get(bom.sku_id, 0)
        need = prep * bom.quantity_per_unit
        total_need[bom.ingredient_id] = total_need.get(bom.ingredient_id, 0) + need

    ingredients = {i.id: i for i in db.query(Ingredient).all()}
    need_total = sum(total_need.values())
    met_total = 0.0
    for ing_id, need in total_need.items():
        ing = ingredients.get(ing_id)
        if ing:
            met_total += min(ing.stock_on_hand, need)

    return met_total / need_total if need_total > 0 else 1.0


def detect_stockout_risk(target_date: date, db: Session) -> list[StockoutAlert]:
    outlets = db.query(Outlet).filter(Outlet.is_active == True).all()
    skus = db.query(SKU).filter(SKU.is_active == True).all()

    # Get latest prep plan for target_date
    prep_plan = (
        db.query(PrepPlan)
        .filter(PrepPlan.plan_date == target_date)
        .order_by(PrepPlan.created_at.desc())
        .first()
    )
    prep_map: dict[tuple, int] = {}
    if prep_plan:
        for line in prep_plan.lines:
            qty = line.edited_units if line.edited_units is not None else line.recommended_units
            prep_map[(line.outlet_id, line.sku_id, line.daypart)] = qty

    ingredient_coverage = _get_ingredient_coverage(db, target_date)

    alerts: list[StockoutAlert] = []

    for outlet in outlets:
        ingredient_alert_emitted = False
        for sku in skus:
            current_stock = _get_stock(db, outlet.id, sku.id)
            fc = forecast_demand(outlet.id, sku.id, target_date, db)

            threshold = (
                BESTSELLER_COVERAGE_THRESHOLD if sku.is_bestseller
                else STANDARD_COVERAGE_THRESHOLD
            )

            # Check morning stockout: morning forecast > stock + morning prep arriving before 7am
            morning_prep = prep_map.get((outlet.id, sku.id, "morning"), 0)
            total_morning_available = current_stock + morning_prep
            morning_demand = fc.morning

            morning_alert_added = False
            if morning_demand > 0:
                morning_coverage = total_morning_available / morning_demand
                if morning_coverage < threshold:
                    shortage = morning_demand - total_morning_available
                    risk = "high" if sku.is_bestseller else "medium"
                    alerts.append(StockoutAlert(
                        outlet_id=outlet.id,
                        outlet_name=outlet.name,
                        sku_id=sku.id,
                        sku_name=sku.name,
                        affected_daypart="morning",
                        risk_level=risk,
                        shortage_qty=round(shortage, 1),
                        reason=(
                            f"Morning stock ({total_morning_available}) covers only "
                            f"{morning_coverage:.0%} of forecast ({morning_demand:.0f})"
                        ),
                        coverage_pct=round(morning_coverage * 100, 1),
                    ))
                    morning_alert_added = True

            recent_morning_peak = _get_recent_daypart_peak(db, outlet.id, sku.id, "morning", target_date)
            if (
                not morning_alert_added
                and recent_morning_peak > morning_demand
                and recent_morning_peak > 0
            ):
                peak_coverage = total_morning_available / recent_morning_peak
                if peak_coverage < threshold:
                    shortage = recent_morning_peak - total_morning_available
                    risk = "high" if sku.is_bestseller else "medium"
                    alerts.append(StockoutAlert(
                        outlet_id=outlet.id,
                        outlet_name=outlet.name,
                        sku_id=sku.id,
                        sku_name=sku.name,
                        affected_daypart="morning",
                        risk_level=risk,
                        shortage_qty=round(shortage, 1),
                        reason=(
                            f"Recent morning peak demand ({recent_morning_peak}) exceeds planned "
                            f"availability ({total_morning_available})"
                        ),
                        coverage_pct=round(peak_coverage * 100, 1),
                    ))

            # Check ingredient coverage for production
            if ingredient_coverage < STANDARD_COVERAGE_THRESHOLD and not ingredient_alert_emitted:
                for dp in DAYPARTS:
                    dp_demand = getattr(fc, dp)
                    if dp_demand > 0:
                        alerts.append(StockoutAlert(
                            outlet_id=outlet.id,
                            outlet_name=outlet.name,
                            sku_id=sku.id,
                            sku_name=sku.name,
                            affected_daypart=dp,
                            risk_level="high",
                            shortage_qty=round(dp_demand * (1 - ingredient_coverage), 1),
                            reason=(
                                f"Ingredient stock covers only {ingredient_coverage:.0%} "
                                f"of planned production"
                            ),
                            coverage_pct=round(ingredient_coverage * 100, 1),
                        ))
                ingredient_alert_emitted = True

    alerts.sort(key=lambda a: (0 if a.risk_level == "high" else 1))
    return alerts
