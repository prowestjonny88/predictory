from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from db.models import ForecastLine, PrepPlanLine, SKU
from services.model_loader import ModelArtifactError, get_model_artifacts


@dataclass(frozen=True)
class ForecastBand:
    p10: float
    p50: float
    p90: float
    source: str


def _find_band(rows: list[dict[str, Any]], **criteria: str) -> dict[str, Any] | None:
    for row in rows:
        if all(str(row.get(key, "")).lower() == str(value).lower() for key, value in criteria.items()):
            return row
    return None


def _residual_band(
    *,
    sku_code: str,
    outlet_code: str,
    sku_category: str,
    daypart: str,
) -> tuple[float, float, str]:
    artifacts = get_model_artifacts()
    artifacts.validate_for_inference()
    bands = artifacts.residual_bands or {}

    row = _find_band(
        bands.get("sku_outlet_daypart_bands") or [],
        sku_id=sku_code,
        outlet_id=outlet_code,
        daypart=daypart,
    )
    if row:
        return float(row["residual_p10"]), float(row["residual_p90"]), "sku_outlet_daypart"

    row = _find_band(
        bands.get("sku_daypart_bands") or [],
        sku_id=sku_code,
        daypart=daypart,
    )
    if row:
        return float(row["residual_p10"]), float(row["residual_p90"]), "sku_daypart"

    row = _find_band(
        bands.get("category_daypart_bands") or [],
        sku_category=sku_category,
        daypart=daypart,
    )
    if row:
        return float(row["residual_p10"]), float(row["residual_p90"]), "category_daypart"

    row = bands.get("global_residual_band")
    if not row:
        raise ModelArtifactError("Residual band artifact has no global residual band")
    return float(row["residual_p10"]), float(row["residual_p90"]), "global"


def build_forecast_band(
    *,
    p50: float,
    sku_code: str,
    outlet_code: str,
    sku_category: str,
    daypart: str,
) -> ForecastBand:
    lower_residual, upper_residual, source = _residual_band(
        sku_code=sku_code,
        outlet_code=outlet_code,
        sku_category=sku_category,
        daypart=daypart,
    )
    expected = round(max(0.0, p50), 2)
    p10 = round(min(expected, max(0.0, expected + lower_residual)), 2)
    p90 = round(max(expected, expected + upper_residual), 2)
    return ForecastBand(p10=p10, p50=expected, p90=p90, source=source)


def band_for_forecast_line(
    *,
    forecast_line: ForecastLine,
    sku: SKU,
    outlet_code: str,
    daypart: str,
) -> ForecastBand:
    p50 = float(getattr(forecast_line, daypart, forecast_line.total))
    return build_forecast_band(
        p50=p50,
        sku_code=sku.code,
        outlet_code=outlet_code,
        sku_category=sku.category,
        daypart=daypart,
    )


def band_for_prep_line(
    *,
    prep_line: PrepPlanLine,
    forecast_line: ForecastLine,
    sku: SKU,
    outlet_code: str,
) -> ForecastBand:
    return band_for_forecast_line(
        forecast_line=forecast_line,
        sku=sku,
        outlet_code=outlet_code,
        daypart=prep_line.daypart,
    )
