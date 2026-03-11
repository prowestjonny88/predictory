"""
Baseline demand forecasting engine — Task 5
forecast_demand(outlet_id, sku_id, target_date, db) -> ForecastResult
"""
from datetime import date, timedelta
from typing import Optional
import statistics

from sqlalchemy.orm import Session

from db.models import SalesFact, ForecastRun, ForecastLine

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


def _to_daily_totals(daily_sales: dict[date, dict]) -> dict[date, float]:
    return {
        d: float(sum(values.get(dp, 0) for dp in DAYPARTS))
        for d, values in daily_sales.items()
    }


def _weighted_recent_total(daily_totals: dict[date, float], target_date: date) -> float:
    """Weighted 7-day recent trend on total demand."""
    weighted = 0.0
    for i, weight in enumerate(WEIGHTS_7):  # i=0 oldest, i=6 newest
        day = target_date - timedelta(days=7 - i)
        weighted += daily_totals.get(day, 0.0) * weight
    return weighted


def _weekday_pattern_total(daily_totals: dict[date, float], target_date: date) -> float:
    """Average of last 4 same-weekday totals."""
    weekday = target_date.weekday()
    matching_days = sorted(
        [d for d in daily_totals if d.weekday() == weekday and d < target_date],
        reverse=True,
    )[:4]
    if not matching_days:
        return 0.0
    vals = [daily_totals[d] for d in matching_days]
    return float(statistics.mean(vals)) if vals else 0.0


def _moving_average_14_total(daily_totals: dict[date, float], target_date: date) -> float:
    """14-day moving average on total demand."""
    total = 0.0
    count = 0
    window_days = [target_date - timedelta(days=i) for i in range(1, 15)]
    for day in window_days:
        if day in daily_totals:
            total += daily_totals[day]
            count += 1
    return total / count if count > 0 else 0.0


def _historical_daypart_ratios(daily_sales: dict[date, dict], target_date: date, lookback_days: int = 28) -> dict[str, float]:
    """Compute daypart split from recent history for this outlet/SKU."""
    start = target_date - timedelta(days=lookback_days)
    totals = {dp: 0.0 for dp in DAYPARTS}

    for day, values in daily_sales.items():
        if start <= day < target_date:
            for dp in DAYPARTS:
                totals[dp] += float(values.get(dp, 0))

    grand_total = sum(totals.values())
    if grand_total <= 0:
        return {"morning": 1 / 3, "midday": 1 / 3, "evening": 1 / 3}

    return {dp: totals[dp] / grand_total for dp in DAYPARTS}


def forecast_demand(
    outlet_id: int,
    sku_id: int,
    target_date: date,
    db: Session,
) -> ForecastResult:
    """
    Combined total demand forecast:
    0.4 × weighted_recent + 0.4 × weekday_pattern + 0.2 × 14-day MA
    Then split into dayparts using historical daypart ratios.
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

    daily_totals = _to_daily_totals(daily_sales)
    weighted_total = _weighted_recent_total(daily_totals, target_date)
    weekday_total = _weekday_pattern_total(daily_totals, target_date)
    ma14_total = _moving_average_14_total(daily_totals, target_date)

    combined_total = max(0.0, (0.40 * weighted_total) + (0.40 * weekday_total) + (0.20 * ma14_total))
    daypart_ratios = _historical_daypart_ratios(daily_sales, target_date)

    combined = {dp: combined_total * daypart_ratios[dp] for dp in DAYPARTS}
    total = sum(combined.values())

    # Determine weekday labelling
    day_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    reason_tags = []
    if target_date.weekday() >= 5:
        reason_tags.append("Weekend boost")
    if combined["morning"] > (combined["midday"] + combined["evening"]):
        reason_tags.append("Morning peak")
    if total > 0 and ma14_total > 0:
        if total > ma14_total * 1.1:
            reason_tags.append("Above recent average")
        elif total < ma14_total * 0.9:
            reason_tags.append("Declining trend")

    rationale = {
        "weighted_recent_total": round(weighted_total, 1),
        "weekday_pattern_total": round(weekday_total, 1),
        "moving_avg_14d_total": round(ma14_total, 1),
        "historical_daypart_ratios": {k: round(v, 3) for k, v in daypart_ratios.items()},
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
