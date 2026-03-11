"""
Baseline demand forecasting engine — Task 5
forecast_demand(outlet_id, sku_id, target_date, db) -> ForecastResult
"""
from datetime import date, timedelta
from typing import Optional
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import func

from db.models import SalesFact, ForecastRun, ForecastLine, SKU, Outlet

WEIGHTS_7 = [0.05, 0.05, 0.10, 0.10, 0.15, 0.20, 0.35]  # oldest → most recent
DAYPARTS = ["morning", "midday", "evening"]


class ForecastResult:
    def __init__(
        self,
        outlet_id: int,
        sku_id: int,
        target_date: date,
        morning: float,
        midday: float,
        evening: float,
        total: float,
        method: str = "weighted_blend",
        confidence: float = 0.80,
        rationale: Optional[dict] = None,
    ):
        self.outlet_id = outlet_id
        self.sku_id = sku_id
        self.target_date = target_date
        self.morning = morning
        self.midday = midday
        self.evening = evening
        self.total = total
        self.method = method
        self.confidence = confidence
        self.rationale = rationale or {}

    def to_dict(self) -> dict:
        return {
            "outlet_id": self.outlet_id,
            "sku_id": self.sku_id,
            "date": str(self.target_date),
            "morning": round(self.morning, 1),
            "midday": round(self.midday, 1),
            "evening": round(self.evening, 1),
            "total": round(self.total, 1),
            "method": self.method,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


def _get_daily_sales(db: Session, outlet_id: int, sku_id: int, start: date, end: date) -> dict[date, dict]:
    """Returns {sale_date: {daypart: units_sold}}"""
    rows = (
        db.query(SalesFact)
        .filter(
            SalesFact.outlet_id == outlet_id,
            SalesFact.sku_id == sku_id,
            SalesFact.sale_date >= start,
            SalesFact.sale_date < end,
        )
        .all()
    )
    result: dict[date, dict] = {}
    for r in rows:
        d = result.setdefault(r.sale_date, {"morning": 0, "midday": 0, "evening": 0})
        d[r.daypart] = r.units_sold
    return result


def _weighted_recent(daily_sales: dict[date, dict], target_date: date) -> dict[str, float]:
    """Weighted 7-day recent trend (Task 5 spec)."""
    weighted: dict[str, float] = {dp: 0.0 for dp in DAYPARTS}
    for i, w in enumerate(WEIGHTS_7):  # i=0 oldest, i=6 newest
        day = target_date - timedelta(days=7 - i)
        if day in daily_sales:
            for dp in DAYPARTS:
                weighted[dp] += daily_sales[day].get(dp, 0) * w
    return weighted


def _weekday_pattern(daily_sales: dict[date, dict], target_date: date) -> dict[str, float]:
    """Average of last 4 same-weekday sales (Task 5 spec)."""
    weekday = target_date.weekday()
    matching_days = sorted(
        [d for d in daily_sales if d.weekday() == weekday and d < target_date],
        reverse=True,
    )[:4]
    if not matching_days:
        return {dp: 0.0 for dp in DAYPARTS}
    pattern: dict[str, float] = {}
    for dp in DAYPARTS:
        vals = [daily_sales[d].get(dp, 0) for d in matching_days]
        pattern[dp] = statistics.mean(vals) if vals else 0.0
    return pattern


def _moving_average_14(daily_sales: dict[date, dict], target_date: date) -> dict[str, float]:
    """14-day moving average (Task 5 spec)."""
    avg: dict[str, float] = {dp: 0.0 for dp in DAYPARTS}
    window_days = [target_date - timedelta(days=i) for i in range(1, 15)]
    counts: dict[str, int] = {dp: 0 for dp in DAYPARTS}
    for d in window_days:
        if d in daily_sales:
            for dp in DAYPARTS:
                avg[dp] += daily_sales[d].get(dp, 0)
                counts[dp] += 1
    for dp in DAYPARTS:
        avg[dp] = avg[dp] / counts[dp] if counts[dp] > 0 else 0.0
    return avg


def forecast_demand(
    outlet_id: int,
    sku_id: int,
    target_date: date,
    db: Session,
) -> ForecastResult:
    """
    Combined forecast = 0.4 × weighted_recent + 0.4 × weekday_pattern + 0.2 × 14-day MA
    """
    history_start = target_date - timedelta(days=60)
    daily_sales = _get_daily_sales(db, outlet_id, sku_id, history_start, target_date)

    if not daily_sales:
        # No history — return zeros
        return ForecastResult(
            outlet_id=outlet_id, sku_id=sku_id, target_date=target_date,
            morning=0, midday=0, evening=0, total=0,
            method="no_history", confidence=0.30,
            rationale={"note": "No historical data available"},
        )

    weighted = _weighted_recent(daily_sales, target_date)
    weekday = _weekday_pattern(daily_sales, target_date)
    ma14 = _moving_average_14(daily_sales, target_date)

    combined: dict[str, float] = {}
    for dp in DAYPARTS:
        combined[dp] = (
            0.40 * weighted.get(dp, 0)
            + 0.40 * weekday.get(dp, 0)
            + 0.20 * ma14.get(dp, 0)
        )
        combined[dp] = max(0.0, combined[dp])

    total = sum(combined.values())

    # Determine weekday labelling
    day_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    reason_tags = []
    if target_date.weekday() >= 5:
        reason_tags.append("Weekend boost")
    if combined["morning"] > (combined["midday"] + combined["evening"]):
        reason_tags.append("Morning peak")
    if total > 0 and ma14:
        ma_total = sum(ma14.values())
        if total > ma_total * 1.1:
            reason_tags.append("Above recent average")
        elif total < ma_total * 0.9:
            reason_tags.append("Declining trend")

    rationale = {
        "weighted_recent": {k: round(v, 1) for k, v in weighted.items()},
        "weekday_pattern": {k: round(v, 1) for k, v in weekday.items()},
        "moving_avg_14d": {k: round(v, 1) for k, v in ma14.items()},
        "reason_tags": reason_tags,
        "target_weekday": day_labels[target_date.weekday()],
    }

    return ForecastResult(
        outlet_id=outlet_id,
        sku_id=sku_id,
        target_date=target_date,
        morning=combined["morning"],
        midday=combined["midday"],
        evening=combined["evening"],
        total=total,
        method="weighted_blend",
        confidence=0.82,
        rationale=rationale,
    )


def run_forecast_for_date(target_date: date, db: Session) -> ForecastRun:
    """Generate a ForecastRun for all outlet × SKU combinations and persist."""
    from db.models import Outlet, SKU

    outlets = db.query(Outlet).filter(Outlet.is_active == True).all()
    skus = db.query(SKU).filter(SKU.is_active == True).all()

    run = ForecastRun(forecast_date=target_date, status="completed")
    db.add(run)
    db.flush()

    for outlet in outlets:
        for sku in skus:
            result = forecast_demand(outlet.id, sku.id, target_date, db)
            line = ForecastLine(
                run_id=run.id,
                outlet_id=outlet.id,
                sku_id=sku.id,
                morning=result.morning,
                midday=result.midday,
                evening=result.evening,
                total=result.total,
                method=result.method,
                confidence=result.confidence,
                rationale_json=result.rationale,
            )
            db.add(line)

    db.commit()
    db.refresh(run)
    return run
