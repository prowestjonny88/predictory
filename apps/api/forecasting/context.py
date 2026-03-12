import os
import statistics
from datetime import date as date_type, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.models import ForecastOverride, HolidayCalendar, InventorySnapshot, Outlet, SalesFact
from forecasting.weather import get_or_refresh_weather_snapshot

DEFAULT_COUNTRY_CODE = os.getenv("HOLIDAY_DEFAULT_COUNTRY", "MY")
SNAPSHOT_PRIORITY = {"morning": 0, "midday": 1, "evening": 2, "eod": 3}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _format_pct(value: float) -> str:
    return f"{value:.1f}%"


def _serialize_override(override: ForecastOverride) -> dict:
    return {
        "id": override.id,
        "target_date": str(override.target_date),
        "outlet_id": override.outlet_id,
        "sku_id": override.sku_id,
        "sku_name": override.sku.name if override.sku else None,
        "override_type": override.override_type,
        "title": override.title,
        "notes": override.notes,
        "adjustment_pct": override.adjustment_pct,
        "enabled": override.enabled,
        "created_by": override.created_by,
    }


def get_holiday_signal(target_date: date_type, db: Session) -> Optional[dict]:
    holiday = (
        db.query(HolidayCalendar)
        .filter(
            HolidayCalendar.holiday_date == target_date,
            HolidayCalendar.country_code == DEFAULT_COUNTRY_CODE,
            HolidayCalendar.is_active == True,
        )
        .order_by(HolidayCalendar.id.asc())
        .first()
    )
    if not holiday:
        return None

    details = [holiday.holiday_type or "Holiday"]
    if holiday.region_code:
        details.append(f"Region: {holiday.region_code}")
    if holiday.demand_uplift_pct:
        details.append(f"Configured uplift {_format_pct(holiday.demand_uplift_pct)}")

    return {
        "label": holiday.name,
        "source": holiday.source,
        "status": "applied" if holiday.demand_uplift_pct else "flagged",
        "adjustment_pct": round(holiday.demand_uplift_pct, 1),
        "details": details,
    }


def get_weather_signal(outlet: Outlet, target_date: date_type, db: Session) -> dict:
    snapshot = get_or_refresh_weather_snapshot(outlet, target_date, db)
    details = []
    if snapshot.rain_mm is not None:
        details.append(f"Rain forecast {snapshot.rain_mm:.1f} mm")
    if snapshot.temp_max_c is not None:
        details.append(f"Max temp {snapshot.temp_max_c:.1f}C")
    if not details:
        details.append(snapshot.summary)

    return {
        "label": snapshot.summary,
        "source": snapshot.source,
        "status": snapshot.status,
        "adjustment_pct": round(snapshot.adjustment_pct, 1),
        "details": details,
    }


def get_matching_overrides(
    target_date: date_type,
    outlet_id: int,
    db: Session,
    sku_id: int | None = None,
) -> tuple[list[ForecastOverride], float]:
    overrides = (
        db.query(ForecastOverride)
        .filter(
            ForecastOverride.target_date == target_date,
            ForecastOverride.outlet_id == outlet_id,
        )
        .order_by(ForecastOverride.created_at.desc())
        .all()
    )

    applicable = []
    adjustment_pct = 0.0
    for override in overrides:
        if not override.enabled:
            continue
        if sku_id is not None:
            if override.sku_id is None or override.sku_id == sku_id:
                applicable.append(override)
                adjustment_pct += override.adjustment_pct
        else:
            applicable.append(override)
            if override.sku_id is None:
                adjustment_pct += override.adjustment_pct

    return applicable, _clamp(adjustment_pct, -50.0, 100.0)


def _load_daily_totals_for_sku(
    outlet_id: int,
    sku_id: int,
    target_date: date_type,
    db: Session,
    lookback_days: int = 60,
) -> dict[date_type, float]:
    rows = (
        db.query(SalesFact)
        .filter(
            SalesFact.outlet_id == outlet_id,
            SalesFact.sku_id == sku_id,
            SalesFact.sale_date >= target_date - timedelta(days=lookback_days),
            SalesFact.sale_date < target_date,
        )
        .all()
    )
    totals: dict[date_type, float] = {}
    for row in rows:
        totals[row.sale_date] = totals.get(row.sale_date, 0.0) + float(row.units_sold)
    return totals


def _get_best_inventory_levels(
    outlet_id: int,
    sku_id: int,
    target_date: date_type,
    db: Session,
    start_date: date_type,
) -> dict[date_type, int]:
    rows = (
        db.query(InventorySnapshot)
        .filter(
            InventorySnapshot.outlet_id == outlet_id,
            InventorySnapshot.sku_id == sku_id,
            InventorySnapshot.snapshot_date >= start_date,
            InventorySnapshot.snapshot_date < target_date,
        )
        .all()
    )

    selected: dict[date_type, tuple[int, int]] = {}
    for row in rows:
        rank = SNAPSHOT_PRIORITY.get(row.snapshot_time, -1)
        existing = selected.get(row.snapshot_date)
        if existing is None or rank >= existing[0]:
            selected[row.snapshot_date] = (rank, row.units_on_hand)

    return {key: value[1] for key, value in selected.items()}


def analyze_stockout_censoring(
    outlet_id: int,
    sku_id: Optional[int],
    target_date: date_type,
    daily_totals: Optional[dict[date_type, float]],
    db: Session,
) -> dict:
    if sku_id is None:
        return {
            "enabled": False,
            "adjusted_history_days": 0,
            "adjusted_dates": [],
            "note": "Select a SKU to inspect stockout recovery.",
            "adjustments": [],
            "adjusted_daily_totals": daily_totals or {},
        }

    observed = daily_totals or _load_daily_totals_for_sku(outlet_id, sku_id, target_date, db)
    if not observed:
        return {
            "enabled": True,
            "adjusted_history_days": 0,
            "adjusted_dates": [],
            "note": "No historical sales found for stockout recovery.",
            "adjustments": [],
            "adjusted_daily_totals": {},
        }

    start_date = min(observed)
    inventory_levels = _get_best_inventory_levels(outlet_id, sku_id, target_date, db, start_date)
    adjusted = dict(observed)
    adjustments = []

    ordered_days = sorted(observed)
    for day in ordered_days:
        available_stock = inventory_levels.get(day)
        if available_stock is None or available_stock > 2:
            continue

        previous_days = [candidate for candidate in ordered_days if candidate < day][-7:]
        if not previous_days:
            continue

        recent_values = [observed[candidate] for candidate in previous_days]
        recent_median = statistics.median(recent_values)
        observed_total = observed[day]
        if recent_median <= 0 or observed_total < recent_median * 0.9:
            continue

        same_weekday_days = [
            candidate for candidate in ordered_days if candidate < day and candidate.weekday() == day.weekday()
        ][-4:]
        same_weekday_reference = (
            float(statistics.mean(observed[candidate] for candidate in same_weekday_days))
            if same_weekday_days
            else observed_total
        )

        candidate_total = max(observed_total * 1.15, same_weekday_reference, recent_median)
        adjusted_total = min(candidate_total, observed_total * 1.25)
        adjusted_total = round(adjusted_total, 1)

        if adjusted_total > observed_total:
            adjusted[day] = adjusted_total
            adjustments.append(
                {
                    "date": str(day),
                    "observed_total": round(observed_total, 1),
                    "adjusted_total": adjusted_total,
                    "inventory_units": available_stock,
                }
            )

    if not adjustments:
        note = "No likely stockout-censored days were detected."
    else:
        note = "Recovered likely lost sales from low end-of-day stock history."

    return {
        "enabled": True,
        "adjusted_history_days": len(adjustments),
        "adjusted_dates": [item["date"] for item in adjustments],
        "note": note,
        "adjustments": adjustments,
        "adjusted_daily_totals": adjusted,
    }


def build_forecast_context(
    *,
    outlet_id: int,
    target_date: date_type,
    db: Session,
    sku_id: int | None = None,
    daily_totals: Optional[dict[date_type, float]] = None,
) -> dict:
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not outlet:
        raise ValueError(f"Outlet {outlet_id} not found")

    holiday = get_holiday_signal(target_date, db)
    weather = get_weather_signal(outlet, target_date, db)
    overrides, manual_override_pct = get_matching_overrides(target_date, outlet_id, db, sku_id=sku_id)
    stockout_censoring = analyze_stockout_censoring(outlet_id, sku_id, target_date, daily_totals, db)

    holiday_pct = (holiday or {}).get("adjustment_pct", 0.0)
    weather_pct = weather.get("adjustment_pct", 0.0)
    combined_adjustment_pct = _clamp(holiday_pct + weather_pct + manual_override_pct, -60.0, 120.0)

    return {
        "target_date": str(target_date),
        "outlet_id": outlet_id,
        "sku_id": sku_id,
        "holiday": holiday,
        "weather": weather,
        "stockout_censoring": {
            "enabled": stockout_censoring["enabled"],
            "adjusted_history_days": stockout_censoring["adjusted_history_days"],
            "adjusted_dates": stockout_censoring["adjusted_dates"],
            "note": stockout_censoring["note"],
        },
        "active_overrides": [_serialize_override(override) for override in overrides],
        "combined_adjustment_pct": round(combined_adjustment_pct, 1),
        "_holiday_pct": holiday_pct,
        "_weather_pct": weather_pct,
        "_manual_override_pct": manual_override_pct,
        "_stockout_censoring": stockout_censoring,
    }
