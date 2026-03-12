"""
Baseline demand forecasting engine - Task 5
forecast_demand(outlet_id, sku_id, target_date, db) -> ForecastResult
"""
from datetime import date, timedelta
from typing import Optional
import statistics

from sqlalchemy.orm import Session

from db.models import ForecastLine, ForecastRun, SalesFact
from forecasting.context import build_forecast_context

WEIGHTS_7 = [0.05, 0.05, 0.10, 0.10, 0.15, 0.20, 0.35]
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
    for row in rows:
        bucket = result.setdefault(row.sale_date, {"morning": 0, "midday": 0, "evening": 0})
        bucket[row.daypart] = row.units_sold
    return result


def _to_daily_totals(daily_sales: dict[date, dict]) -> dict[date, float]:
    return {
        sale_date: float(sum(values.get(daypart, 0) for daypart in DAYPARTS))
        for sale_date, values in daily_sales.items()
    }


def _weighted_recent_total(daily_totals: dict[date, float], target_date: date) -> float:
    weighted = 0.0
    for index, weight in enumerate(WEIGHTS_7):
        day = target_date - timedelta(days=7 - index)
        weighted += daily_totals.get(day, 0.0) * weight
    return weighted


def _recent_signal_available(daily_totals: dict[date, float], target_date: date) -> bool:
    return any((target_date - timedelta(days=i)) in daily_totals for i in range(1, 8))


def _weekday_pattern_total(daily_totals: dict[date, float], target_date: date) -> float:
    weekday = target_date.weekday()
    matching_days = sorted(
        [day for day in daily_totals if day.weekday() == weekday and day < target_date],
        reverse=True,
    )[:4]
    if not matching_days:
        return 0.0
    return float(statistics.mean(daily_totals[day] for day in matching_days))


def _weekday_signal_available(daily_totals: dict[date, float], target_date: date) -> bool:
    weekday = target_date.weekday()
    return any(day.weekday() == weekday and day < target_date for day in daily_totals)


def _moving_average_14_total(daily_totals: dict[date, float], target_date: date) -> float:
    window_days = [target_date - timedelta(days=i) for i in range(1, 15)]
    values = [daily_totals[day] for day in window_days if day in daily_totals]
    return float(sum(values) / len(values)) if values else 0.0


def _ma14_signal_available(daily_totals: dict[date, float], target_date: date) -> bool:
    return any((target_date - timedelta(days=i)) in daily_totals for i in range(1, 15))


def _blend_total_with_available_signals(
    weighted_total: float,
    weekday_total: float,
    ma14_total: float,
    has_recent: bool,
    has_weekday: bool,
    has_ma14: bool,
) -> tuple[float, dict[str, float]]:
    base_weights = {
        "weighted_recent_total": 0.40,
        "weekday_pattern_total": 0.40,
        "moving_avg_14d_total": 0.20,
    }
    components = {
        "weighted_recent_total": weighted_total,
        "weekday_pattern_total": weekday_total,
        "moving_avg_14d_total": ma14_total,
    }
    availability = {
        "weighted_recent_total": has_recent,
        "weekday_pattern_total": has_weekday,
        "moving_avg_14d_total": has_ma14,
    }

    active_weight = sum(base_weights[name] for name, enabled in availability.items() if enabled)
    if active_weight <= 0:
        return 0.0, {key: 0.0 for key in base_weights}

    applied_weights = {
        name: (base_weights[name] / active_weight if availability[name] else 0.0)
        for name in base_weights
    }
    blended_total = sum(components[name] * applied_weights[name] for name in components)
    return blended_total, applied_weights


def _historical_daypart_ratios(
    daily_sales: dict[date, dict],
    target_date: date,
    lookback_days: int = 28,
) -> dict[str, float]:
    start = target_date - timedelta(days=lookback_days)
    totals = {daypart: 0.0 for daypart in DAYPARTS}

    for sale_date, values in daily_sales.items():
        if start <= sale_date < target_date:
            for daypart in DAYPARTS:
                totals[daypart] += float(values.get(daypart, 0))

    grand_total = sum(totals.values())
    if grand_total <= 0:
        return {"morning": 1 / 3, "midday": 1 / 3, "evening": 1 / 3}

    return {daypart: totals[daypart] / grand_total for daypart in DAYPARTS}


def forecast_demand(
    outlet_id: int,
    sku_id: int,
    target_date: date,
    db: Session,
) -> ForecastResult:
    history_start = target_date - timedelta(days=60)
    daily_sales = _get_daily_sales(db, outlet_id, sku_id, history_start, target_date)

    if not daily_sales:
        context = build_forecast_context(
            outlet_id=outlet_id,
            sku_id=sku_id,
            target_date=target_date,
            db=db,
            daily_totals={},
        )
        return ForecastResult(
            outlet_id=outlet_id,
            sku_id=sku_id,
            target_date=target_date,
            morning=0.0,
            midday=0.0,
            evening=0.0,
            total=0.0,
            method="no_history",
            confidence=0.30,
            rationale={
                "note": "No historical data available",
                "baseline_total": 0.0,
                "holiday_signal": context["holiday"],
                "weather_signal": context["weather"],
                "manual_overrides": context["active_overrides"],
                "stockout_censoring": context["stockout_censoring"],
                "context_adjustment_pct": context["combined_adjustment_pct"],
                "final_total_before_daypart_split": 0.0,
            },
        )

    observed_daily_totals = _to_daily_totals(daily_sales)
    context = build_forecast_context(
        outlet_id=outlet_id,
        sku_id=sku_id,
        target_date=target_date,
        db=db,
        daily_totals=observed_daily_totals,
    )
    stockout_meta = context["_stockout_censoring"]
    adjusted_daily_totals = stockout_meta["adjusted_daily_totals"]

    weighted_total = _weighted_recent_total(adjusted_daily_totals, target_date)
    weekday_total = _weekday_pattern_total(adjusted_daily_totals, target_date)
    ma14_total = _moving_average_14_total(adjusted_daily_totals, target_date)

    has_recent = _recent_signal_available(adjusted_daily_totals, target_date)
    has_weekday = _weekday_signal_available(adjusted_daily_totals, target_date)
    has_ma14 = _ma14_signal_available(adjusted_daily_totals, target_date)

    baseline_total, applied_weights = _blend_total_with_available_signals(
        weighted_total=weighted_total,
        weekday_total=weekday_total,
        ma14_total=ma14_total,
        has_recent=has_recent,
        has_weekday=has_weekday,
        has_ma14=has_ma14,
    )
    baseline_total = max(0.0, baseline_total)
    adjusted_total = max(0.0, baseline_total * (1 + (context["combined_adjustment_pct"] / 100.0)))

    daypart_ratios = _historical_daypart_ratios(daily_sales, target_date)
    combined = {daypart: adjusted_total * daypart_ratios[daypart] for daypart in DAYPARTS}
    total = sum(combined.values())

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
    if context["holiday"]:
        reason_tags.append("Holiday flag")
    if context["weather"]["adjustment_pct"] != 0:
        reason_tags.append("Weather adjustment")
    if context["active_overrides"]:
        reason_tags.append("Manual override")
    if stockout_meta["adjusted_history_days"] > 0:
        reason_tags.append("Recovered stockout history")

    rationale = {
        "weighted_recent_total": round(weighted_total, 1),
        "weekday_pattern_total": round(weekday_total, 1),
        "moving_avg_14d_total": round(ma14_total, 1),
        "baseline_total": round(baseline_total, 1),
        "applied_component_weights": {key: round(value, 3) for key, value in applied_weights.items()},
        "historical_daypart_ratios": {key: round(value, 3) for key, value in daypart_ratios.items()},
        "holiday_signal": context["holiday"],
        "weather_signal": context["weather"],
        "manual_overrides": context["active_overrides"],
        "stockout_censoring": {
            "enabled": stockout_meta["enabled"],
            "adjusted_history_days": stockout_meta["adjusted_history_days"],
            "adjusted_dates": stockout_meta["adjusted_dates"],
            "note": stockout_meta["note"],
            "adjustments": stockout_meta["adjustments"],
        },
        "context_adjustment_pct": round(context["combined_adjustment_pct"], 1),
        "final_total_before_daypart_split": round(adjusted_total, 1),
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
    from db.models import Outlet, SKU

    outlets = db.query(Outlet).filter(Outlet.is_active == True).all()
    skus = db.query(SKU).filter(SKU.is_active == True).all()

    run = ForecastRun(forecast_date=target_date, status="completed")
    db.add(run)
    db.flush()

    for outlet in outlets:
        for sku in skus:
            result = forecast_demand(outlet.id, sku.id, target_date, db)
            db.add(
                ForecastLine(
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
            )

    db.commit()
    db.refresh(run)
    return run
