from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import (
    ForecastOverride,
    Ingredient,
    InventorySnapshot,
    Outlet,
    RecipeBOM,
    SKU,
    SalesFact,
    WasteLog,
    WeatherSnapshot,
)
from services.model_loader import get_model_artifacts
from services.uncertainty import build_forecast_band

DAYPARTS = ("morning", "midday", "evening")
ENGINE_NAME = "lightgbm_mlops_prototype"
MODEL_METHOD = "lightgbm_p50_v1"


class OperationalDataError(RuntimeError):
    """Raised when real operational data required for live inference is missing."""


class FeatureBuildError(RuntimeError):
    """Raised when LightGBM feature rows cannot be constructed."""


@dataclass(frozen=True)
class DaypartPrediction:
    daypart: str
    p50: float
    p10: float
    p90: float
    uncertainty_source: str
    encoded_features: dict[str, float]
    raw_features: dict[str, Any]


@dataclass(frozen=True)
class SkuOutletPrediction:
    outlet_id: int
    sku_id: int
    morning: float
    midday: float
    evening: float
    total: float
    dayparts: list[DaypartPrediction]


def _schema_defaults() -> dict[str, float]:
    schema = get_model_artifacts().feature_schema or {}
    return schema.get("numeric_imputation_values") or {}


def _encoded_columns() -> list[str]:
    schema = get_model_artifacts().encoded_feature_schema or {}
    columns = schema.get("encoded_feature_columns") or []
    if not columns:
        raise FeatureBuildError("Encoded feature schema has no columns")
    return list(columns)


def _safe_float(value: Any, default: float | None = None) -> float:
    if value is None:
        if default is None:
            raise FeatureBuildError("Missing numeric value")
        return float(default)
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        if default is None:
            raise FeatureBuildError(f"Invalid numeric value: {value}") from exc
        return float(default)
    if math.isnan(result):
        if default is None:
            raise FeatureBuildError("NaN numeric value")
        return float(default)
    return result


def _historical_sales(
    db: Session,
    *,
    outlet_id: int,
    sku_id: int,
    daypart: str,
    target_date: date,
    lookback_days: int = 60,
) -> dict[date, float]:
    rows = (
        db.query(SalesFact)
        .filter(
            SalesFact.outlet_id == outlet_id,
            SalesFact.sku_id == sku_id,
            SalesFact.daypart == daypart,
            SalesFact.sale_date >= target_date - timedelta(days=lookback_days),
            SalesFact.sale_date < target_date,
        )
        .all()
    )
    return {row.sale_date: float(row.units_sold or 0) for row in rows}


def _historical_waste(
    db: Session,
    *,
    outlet_id: int,
    sku_id: int,
    daypart: str,
    target_date: date,
    lookback_days: int = 60,
) -> dict[date, float]:
    rows = (
        db.query(WasteLog)
        .filter(
            WasteLog.outlet_id == outlet_id,
            WasteLog.sku_id == sku_id,
            WasteLog.daypart == daypart,
            WasteLog.waste_date >= target_date - timedelta(days=lookback_days),
            WasteLog.waste_date < target_date,
        )
        .all()
    )
    return {row.waste_date: float(row.units_wasted or 0) for row in rows}


def _inventory_by_date(
    db: Session,
    *,
    outlet_id: int,
    sku_id: int,
    target_date: date,
    lookback_days: int = 60,
) -> dict[date, float]:
    priority = {"morning": 0, "midday": 1, "evening": 2, "eod": 3}
    rows = (
        db.query(InventorySnapshot)
        .filter(
            InventorySnapshot.outlet_id == outlet_id,
            InventorySnapshot.sku_id == sku_id,
            InventorySnapshot.snapshot_date >= target_date - timedelta(days=lookback_days),
            InventorySnapshot.snapshot_date < target_date,
        )
        .all()
    )
    selected: dict[date, tuple[int, float]] = {}
    for row in rows:
        rank = priority.get(row.snapshot_time, -1)
        current = selected.get(row.snapshot_date)
        if current is None or rank >= current[0]:
            selected[row.snapshot_date] = (rank, float(row.units_on_hand or 0))
    return {snapshot_date: value for snapshot_date, (_rank, value) in selected.items()}


def _value_on_day(values: dict[date, float], target_date: date, days_back: int, default: float) -> float:
    return values.get(target_date - timedelta(days=days_back), default)


def _window(values: dict[date, float], target_date: date, days: int) -> list[float]:
    return [values[day] for day in (target_date - timedelta(days=i) for i in range(1, days + 1)) if day in values]


def _mean(values: list[float], default: float) -> float:
    return float(sum(values) / len(values)) if values else default


def _median(values: list[float], default: float) -> float:
    return float(statistics.median(values)) if values else default


def _std(values: list[float], default: float) -> float:
    return float(statistics.stdev(values)) if len(values) > 1 else default


def _max(values: list[float], default: float) -> float:
    return float(max(values)) if values else default


def _rate(flags: list[float], default: float) -> float:
    return float(sum(flags) / len(flags)) if flags else default


def _unit_cost(sku: SKU, db: Session, defaults: dict[str, float]) -> float:
    total = 0.0
    rows = db.query(RecipeBOM).filter(RecipeBOM.sku_id == sku.id).all()
    for row in rows:
        ingredient = db.query(Ingredient).filter(Ingredient.id == row.ingredient_id).first()
        if ingredient:
            total += float(ingredient.cost_per_unit or 0) * float(row.quantity_per_unit or 0)
    return round(total, 4) if total > 0 else float(defaults["unit_cost"])


def _weather(db: Session, outlet_id: int, target_date: date, defaults: dict[str, float]) -> tuple[str, float, float]:
    snapshot = (
        db.query(WeatherSnapshot)
        .filter(WeatherSnapshot.outlet_id == outlet_id, WeatherSnapshot.target_date == target_date)
        .first()
    )
    if not snapshot:
        raise OperationalDataError(f"No weather snapshot for outlet {outlet_id} on {target_date}")
    rain = _safe_float(snapshot.rain_mm, defaults["rain_mm"])
    temp = _safe_float(snapshot.temp_max_c, defaults["temperature"])
    if rain >= 10:
        condition = "heavy_rain"
    elif rain >= 2:
        condition = "rain"
    elif rain > 0:
        condition = "light_rain"
    else:
        condition = "clear"
    return condition, rain, temp


def _holiday(db: Session, target_date: date) -> tuple[float, float]:
    from db.models import HolidayCalendar

    holiday = (
        db.query(HolidayCalendar)
        .filter(HolidayCalendar.holiday_date == target_date, HolidayCalendar.is_active == True)
        .order_by(HolidayCalendar.id.asc())
        .first()
    )
    if not holiday:
        return 0.0, 0.0
    return 1.0, float(holiday.demand_uplift_pct or 0.0)


def _overrides(db: Session, *, target_date: date, outlet_id: int, sku_id: int) -> tuple[float, float, float, float, str]:
    rows = (
        db.query(ForecastOverride)
        .filter(
            ForecastOverride.target_date == target_date,
            ForecastOverride.outlet_id == outlet_id,
            ForecastOverride.enabled == True,
        )
        .all()
    )
    promo_uplift = 0.0
    event_uplift = 0.0
    promo_type = ""
    for row in rows:
        if row.sku_id is not None and row.sku_id != sku_id:
            continue
        if row.override_type == "promo":
            promo_uplift += float(row.adjustment_pct or 0.0)
            title = (row.title or "").lower()
            if "bundle" in title:
                promo_type = "bundle"
            elif "member" in title:
                promo_type = "member_deal"
            elif "display" in title:
                promo_type = "display_push"
            elif "social" in title:
                promo_type = "social_post"
        elif row.override_type == "event":
            event_uplift += float(row.adjustment_pct or 0.0)
    return (
        1.0 if promo_uplift else 0.0,
        promo_uplift,
        1.0 if event_uplift else 0.0,
        event_uplift,
        promo_type,
    )


def _cross_demand(
    db: Session,
    *,
    sku_id: int,
    daypart: str,
    target_date: date,
    days_back: int,
    default: float,
) -> float:
    total = (
        db.query(func.sum(SalesFact.units_sold))
        .filter(
            SalesFact.sku_id == sku_id,
            SalesFact.daypart == daypart,
            SalesFact.sale_date == target_date - timedelta(days=days_back),
        )
        .scalar()
    )
    return float(total) if total is not None else default


def _build_raw_features(
    *,
    db: Session,
    outlet: Outlet,
    sku: SKU,
    daypart: str,
    target_date: date,
    defaults: dict[str, float],
) -> dict[str, Any]:
    sales = _historical_sales(
        db,
        outlet_id=outlet.id,
        sku_id=sku.id,
        daypart=daypart,
        target_date=target_date,
    )
    if not sales:
        raise OperationalDataError(
            f"No sales history for outlet '{outlet.code}', SKU '{sku.code}', daypart '{daypart}'"
        )
    waste = _historical_waste(
        db,
        outlet_id=outlet.id,
        sku_id=sku.id,
        daypart=daypart,
        target_date=target_date,
    )
    inventory = _inventory_by_date(
        db,
        outlet_id=outlet.id,
        sku_id=sku.id,
        target_date=target_date,
    )
    if not inventory:
        raise OperationalDataError(
            f"No inventory history for outlet '{outlet.code}', SKU '{sku.code}', daypart '{daypart}'"
        )

    estimated = {day: sales.get(day, 0.0) + waste.get(day, 0.0) for day in set(sales) | set(waste)}
    actual_window_7 = _window(sales, target_date, 7)
    actual_window_14 = _window(sales, target_date, 14)
    estimated_window_7 = _window(estimated, target_date, 7)
    estimated_window_14 = _window(estimated, target_date, 14)
    estimated_window_28 = _window(estimated, target_date, 28)
    waste_window_7 = _window(waste, target_date, 7)
    waste_window_14 = _window(waste, target_date, 14)

    stockout_flags_7 = [1.0 if inventory.get(target_date - timedelta(days=i), 9999.0) <= 0 else 0.0 for i in range(1, 8)]
    stockout_flags_14 = [1.0 if inventory.get(target_date - timedelta(days=i), 9999.0) <= 0 else 0.0 for i in range(1, 15)]
    material_stockout_flags_7 = [1.0 if inventory.get(target_date - timedelta(days=i), 9999.0) <= 2 else 0.0 for i in range(1, 8)]
    material_stockout_flags_14 = [1.0 if inventory.get(target_date - timedelta(days=i), 9999.0) <= 2 else 0.0 for i in range(1, 15)]
    waste_flags_7 = [1.0 if waste.get(target_date - timedelta(days=i), 0.0) > 0 else 0.0 for i in range(1, 8)]
    waste_flags_14 = [1.0 if waste.get(target_date - timedelta(days=i), 0.0) > 0 else 0.0 for i in range(1, 15)]

    weekday = target_date.weekday()
    day_of_year = target_date.timetuple().tm_yday
    is_holiday, holiday_uplift = _holiday(db, target_date)
    weather_condition, rain_mm, temperature = _weather(db, outlet.id, target_date, defaults)
    promo_flag, promo_uplift, event_flag, event_adjustment, promo_type = _overrides(
        db,
        target_date=target_date,
        outlet_id=outlet.id,
        sku_id=sku.id,
    )
    unit_cost = _unit_cost(sku, db, defaults)
    selling_price = float(sku.price or defaults["selling_price"])
    stockout_units_7 = sum(max(0.0, _mean(estimated_window_7, 0.0) - value) for value in actual_window_7)
    stockout_units_14 = sum(max(0.0, _mean(estimated_window_14, 0.0) - value) for value in actual_window_14)

    return {
        "outlet_id": outlet.code,
        "outlet_type": "",
        "sku_id": sku.code,
        "sku_category": sku.category,
        "daypart": daypart,
        "weekday_name": target_date.strftime("%A"),
        "weather_condition": weather_condition,
        "promo_type": promo_type,
        "weekday": float(weekday),
        "is_weekend": 1.0 if weekday >= 5 else 0.0,
        "month": float(target_date.month),
        "week_of_year": float(target_date.isocalendar().week),
        "day_of_year": float(day_of_year),
        "day_of_month": float(target_date.day),
        "weekday_sin": math.sin(2 * math.pi * weekday / 7),
        "weekday_cos": math.cos(2 * math.pi * weekday / 7),
        "day_of_year_sin": math.sin(2 * math.pi * day_of_year / 365),
        "day_of_year_cos": math.cos(2 * math.pi * day_of_year / 365),
        "is_holiday": is_holiday,
        "holiday_uplift_pct": holiday_uplift,
        "rain_mm": rain_mm,
        "temperature": temperature,
        "promo_flag": promo_flag,
        "promo_uplift_pct": promo_uplift,
        "event_flag": event_flag,
        "event_adjustment_pct": event_adjustment,
        "selling_price": selling_price,
        "unit_cost": unit_cost,
        "waste_cost": unit_cost,
        "stockout_cost": max(0.0, selling_price - unit_cost),
        "freshness_hours": float(sku.freshness_hours or defaults["freshness_hours"]),
        "carryover_rate": defaults["carryover_rate"],
        "batch_size": defaults["batch_size"],
        "min_display_qty": defaults["min_display_qty"],
        "lag_1_estimated_demand": _value_on_day(estimated, target_date, 1, defaults["lag_1_estimated_demand"]),
        "lag_2_estimated_demand": _value_on_day(estimated, target_date, 2, defaults["lag_2_estimated_demand"]),
        "lag_7_estimated_demand": _value_on_day(estimated, target_date, 7, defaults["lag_7_estimated_demand"]),
        "lag_14_estimated_demand": _value_on_day(estimated, target_date, 14, defaults["lag_14_estimated_demand"]),
        "lag_28_estimated_demand": _value_on_day(estimated, target_date, 28, defaults["lag_28_estimated_demand"]),
        "lag_1_actual_sales": _value_on_day(sales, target_date, 1, defaults["lag_1_actual_sales"]),
        "lag_7_actual_sales": _value_on_day(sales, target_date, 7, defaults["lag_7_actual_sales"]),
        "rolling_7d_estimated_mean": _mean(estimated_window_7, defaults["rolling_7d_estimated_mean"]),
        "rolling_14d_estimated_mean": _mean(estimated_window_14, defaults["rolling_14d_estimated_mean"]),
        "rolling_28d_estimated_mean": _mean(estimated_window_28, defaults["rolling_28d_estimated_mean"]),
        "rolling_7d_estimated_median": _median(estimated_window_7, defaults["rolling_7d_estimated_median"]),
        "rolling_14d_estimated_median": _median(estimated_window_14, defaults["rolling_14d_estimated_median"]),
        "rolling_7d_estimated_std": _std(estimated_window_7, defaults["rolling_7d_estimated_std"]),
        "rolling_14d_estimated_std": _std(estimated_window_14, defaults["rolling_14d_estimated_std"]),
        "rolling_7d_estimated_max": _max(estimated_window_7, defaults["rolling_7d_estimated_max"]),
        "rolling_14d_estimated_max": _max(estimated_window_14, defaults["rolling_14d_estimated_max"]),
        "rolling_7d_actual_sales_mean": _mean(actual_window_7, defaults["rolling_7d_actual_sales_mean"]),
        "rolling_14d_actual_sales_mean": _mean(actual_window_14, defaults["rolling_14d_actual_sales_mean"]),
        "lag_1_stockout_flag": 1.0 if inventory.get(target_date - timedelta(days=1), 9999.0) <= 0 else 0.0,
        "lag_1_material_stockout_flag": 1.0 if inventory.get(target_date - timedelta(days=1), 9999.0) <= 2 else 0.0,
        "lag_1_waste_flag": 1.0 if waste.get(target_date - timedelta(days=1), 0.0) > 0 else 0.0,
        "lag_1_material_waste_flag": 1.0 if waste.get(target_date - timedelta(days=1), 0.0) > 2 else 0.0,
        "rolling_7d_stockout_rate": _rate(stockout_flags_7, defaults["rolling_7d_stockout_rate"]),
        "rolling_14d_stockout_rate": _rate(stockout_flags_14, defaults["rolling_14d_stockout_rate"]),
        "rolling_7d_material_stockout_rate": _rate(material_stockout_flags_7, defaults["rolling_7d_material_stockout_rate"]),
        "rolling_14d_material_stockout_rate": _rate(material_stockout_flags_14, defaults["rolling_14d_material_stockout_rate"]),
        "rolling_7d_material_waste_rate": _rate(waste_flags_7, defaults["rolling_7d_material_waste_rate"]),
        "rolling_14d_material_waste_rate": _rate(waste_flags_14, defaults["rolling_14d_material_waste_rate"]),
        "rolling_7d_waste_units": sum(waste_window_7) if waste_window_7 else defaults["rolling_7d_waste_units"],
        "rolling_14d_waste_units": sum(waste_window_14) if waste_window_14 else defaults["rolling_14d_waste_units"],
        "rolling_7d_stockout_units": stockout_units_7 if actual_window_7 else defaults["rolling_7d_stockout_units"],
        "rolling_14d_stockout_units": stockout_units_14 if actual_window_14 else defaults["rolling_14d_stockout_units"],
        "rolling_7d_waste_intensity": (sum(waste_window_7) / max(1.0, sum(estimated_window_7))) if estimated_window_7 else defaults["rolling_7d_waste_intensity"],
        "rolling_14d_waste_intensity": (sum(waste_window_14) / max(1.0, sum(estimated_window_14))) if estimated_window_14 else defaults["rolling_14d_waste_intensity"],
        "cross_lag_1_sku_daypart_demand": _cross_demand(db, sku_id=sku.id, daypart=daypart, target_date=target_date, days_back=1, default=defaults["cross_lag_1_sku_daypart_demand"]),
        "cross_lag_7_sku_daypart_demand": _cross_demand(db, sku_id=sku.id, daypart=daypart, target_date=target_date, days_back=7, default=defaults["cross_lag_7_sku_daypart_demand"]),
        "cross_rolling_7d_sku_daypart_demand": _mean(
            [
                _cross_demand(db, sku_id=sku.id, daypart=daypart, target_date=target_date, days_back=i, default=0.0)
                for i in range(1, 8)
            ],
            defaults["cross_rolling_7d_sku_daypart_demand"],
        ),
        "cross_rolling_7d_sku_daypart_stockout_rate": _rate(
            stockout_flags_7,
            defaults["cross_rolling_7d_sku_daypart_stockout_rate"],
        ),
    }


def _encode_features(raw: dict[str, Any], defaults: dict[str, float], columns: list[str]) -> dict[str, float]:
    encoded: dict[str, float] = {}
    categorical_prefixes = (
        "outlet_id",
        "outlet_type",
        "sku_id",
        "sku_category",
        "daypart",
        "weekday_name",
        "weather_condition",
        "promo_type",
    )
    for column in columns:
        matched_category = False
        for prefix in categorical_prefixes:
            marker = f"{prefix}_"
            if column.startswith(marker):
                expected = column[len(marker) :]
                encoded[column] = 1.0 if str(raw.get(prefix, "")) == expected else 0.0
                matched_category = True
                break
        if matched_category:
            continue
        encoded[column] = _safe_float(raw.get(column), defaults.get(column))
    return encoded


def predict_outlet_sku(
    *,
    db: Session,
    outlet: Outlet,
    sku: SKU,
    target_date: date,
) -> SkuOutletPrediction:
    artifacts = get_model_artifacts()
    artifacts.validate_for_inference()
    defaults = _schema_defaults()
    columns = _encoded_columns()
    model = artifacts.model

    rows: list[DaypartPrediction] = []
    for daypart in DAYPARTS:
        raw = _build_raw_features(
            db=db,
            outlet=outlet,
            sku=sku,
            daypart=daypart,
            target_date=target_date,
            defaults=defaults,
        )
        encoded = _encode_features(raw, defaults, columns)
        frame = pd.DataFrame([[encoded[column] for column in columns]], columns=columns)
        prediction = float(model.predict(frame)[0])
        p50 = round(max(0.0, prediction), 2)
        band = build_forecast_band(
            p50=p50,
            sku_code=sku.code,
            outlet_code=outlet.code,
            sku_category=sku.category,
            daypart=daypart,
        )
        rows.append(
            DaypartPrediction(
                daypart=daypart,
                p50=band.p50,
                p10=band.p10,
                p90=band.p90,
                uncertainty_source=band.source,
                encoded_features=encoded,
                raw_features=raw,
            )
        )

    by_daypart = {row.daypart: row.p50 for row in rows}
    total = round(sum(by_daypart.values()), 2)
    return SkuOutletPrediction(
        outlet_id=outlet.id,
        sku_id=sku.id,
        morning=by_daypart["morning"],
        midday=by_daypart["midday"],
        evening=by_daypart["evening"],
        total=total,
        dayparts=rows,
    )
