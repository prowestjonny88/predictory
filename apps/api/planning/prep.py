"""
Prep recommendation engine — Task 6
recommend_prep(outlet_id, sku_id, target_date, forecast, db) -> PrepRecommendation
"""
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from db.models import SKU, InventorySnapshot, WasteLog, PrepPlan, PrepPlanLine
from forecasting.engine import ForecastResult, forecast_demand

DAYPARTS = ["morning", "midday", "evening"]
DEFAULT_SAFETY_BUFFER = 0.10
HIGH_WASTE_THRESHOLD = 0.15  # 15%
HIGH_WASTE_REDUCTION = 0.05  # reduce by 5%


class PrepRecommendation:
    def __init__(
        self,
        outlet_id: int,
        sku_id: int,
        target_date: date,
        morning: int,
        midday: int,
        evening: int,
        current_stock: int,
        rationale: dict,
    ):
        self.outlet_id = outlet_id
        self.sku_id = sku_id
        self.target_date = target_date
        self.morning = morning
        self.midday = midday
        self.evening = evening
        self.current_stock = current_stock
        self.rationale = rationale

    def to_dict(self) -> dict:
        return {
            "outlet_id": self.outlet_id,
            "sku_id": self.sku_id,
            "date": str(self.target_date),
            "morning": self.morning,
            "midday": self.midday,
            "evening": self.evening,
            "total_prep": self.morning + self.midday + self.evening,
            "current_stock": self.current_stock,
            "rationale": self.rationale,
        }


def _get_current_stock(db: Session, outlet_id: int, sku_id: int) -> int:
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


def _get_waste_rate_7d(db: Session, outlet_id: int, sku_id: int, target_date: date) -> float:
    """Returns waste_units / (sold_units + waste_units) over last 7 days."""
    from db.models import SalesFact
    start = target_date - timedelta(days=7)

    waste_rows = db.query(WasteLog).filter(
        WasteLog.outlet_id == outlet_id,
        WasteLog.sku_id == sku_id,
        WasteLog.waste_date >= start,
        WasteLog.waste_date < target_date,
    ).all()
    total_wasted = sum(w.units_wasted for w in waste_rows)

    sales_rows = db.query(SalesFact).filter(
        SalesFact.outlet_id == outlet_id,
        SalesFact.sku_id == sku_id,
        SalesFact.sale_date >= start,
        SalesFact.sale_date < target_date,
    ).all()
    total_sold = sum(s.units_sold for s in sales_rows)

    if total_sold + total_wasted == 0:
        return 0.0
    return total_wasted / (total_sold + total_wasted)


def recommend_prep(
    outlet_id: int,
    sku_id: int,
    target_date: date,
    db: Session,
    forecast: Optional[ForecastResult] = None,
) -> PrepRecommendation:
    """
    prep_qty = forecast_demand + (forecast_demand × safety_buffer_pct) - ready_stock
    Freshness window + waste history adjustments applied.
    """
    sku = db.query(SKU).filter(SKU.id == sku_id).first()
    if not sku:
        raise ValueError(f"SKU {sku_id} not found")

    if forecast is None:
        forecast = forecast_demand(outlet_id, sku_id, target_date, db)

    current_stock = _get_current_stock(db, outlet_id, sku_id)
    waste_rate = _get_waste_rate_7d(db, outlet_id, sku_id, target_date)
    buffer = sku.safety_buffer_pct or DEFAULT_SAFETY_BUFFER

    adjustments = []

    # Apply high-waste-rate reduction
    waste_adj = 1.0
    if waste_rate > HIGH_WASTE_THRESHOLD:
        waste_adj = 1.0 - HIGH_WASTE_REDUCTION
        adjustments.append(f"Waste rate {waste_rate:.1%} > 15%; reduced prep by 5%")

    daypart_forecasts = {
        "morning": forecast.morning,
        "midday": forecast.midday,
        "evening": forecast.evening,
    }

    # Freshness rule from TEAM_PLAN: items with <8h shelf life should not be
    # prepped for evening if a morning batch is already planned.
    short_shelf = sku.freshness_hours < 8

    # Allocate stock against morning first (reduces morning prep)
    stock_remaining = current_stock
    results: dict[str, int] = {}
    for dp in DAYPARTS:
        if short_shelf and dp == "evening" and results.get("morning", 0) > 0:
            results[dp] = 0
            adjustments.append("Short shelf life (<8h): skipped evening prep when morning prep exists")
            continue

        demand = daypart_forecasts[dp] * waste_adj
        stock_for_dp = min(stock_remaining, demand)
        stock_remaining = max(0, stock_remaining - int(stock_for_dp))

        net_demand = demand - stock_for_dp
        prep = max(0, net_demand + (net_demand * buffer))
        results[dp] = round(prep)

    rationale = {
        "safety_buffer_pct": buffer,
        "current_stock": current_stock,
        "waste_rate_7d": round(waste_rate, 3),
        "short_shelf_life": short_shelf,
        "adjustments": adjustments,
        "forecast_used": {
            "morning": round(forecast.morning, 1),
            "midday": round(forecast.midday, 1),
            "evening": round(forecast.evening, 1),
        },
    }

    return PrepRecommendation(
        outlet_id=outlet_id,
        sku_id=sku_id,
        target_date=target_date,
        morning=results["morning"],
        midday=results["midday"],
        evening=results["evening"],
        current_stock=current_stock,
        rationale=rationale,
    )


def generate_prep_plan(target_date: date, db: Session) -> PrepPlan:
    """Generate a full PrepPlan for all outlets × SKUs and persist."""
    from db.models import Outlet, SKU as SKUModel

    outlets = db.query(Outlet).filter(Outlet.is_active == True).all()
    skus = db.query(SKUModel).filter(SKUModel.is_active == True).all()

    plan = PrepPlan(plan_date=target_date, status="draft")
    db.add(plan)
    db.flush()

    for outlet in outlets:
        for sku in skus:
            rec = recommend_prep(outlet.id, sku.id, target_date, db)
            for dp in DAYPARTS:
                line = PrepPlanLine(
                    plan_id=plan.id,
                    outlet_id=outlet.id,
                    sku_id=sku.id,
                    daypart=dp,
                    recommended_units=getattr(rec, dp),
                    current_stock=rec.current_stock if dp == "morning" else 0,
                    rationale_json=rec.rationale,
                    status="pending",
                )
                db.add(line)

    db.commit()
    db.refresh(plan)
    return plan
