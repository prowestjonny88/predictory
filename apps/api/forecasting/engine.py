from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from db.models import ForecastLine, ForecastRun, ModelRun, Outlet, SKU
from services.lightgbm_inference import (
    ENGINE_NAME,
    MODEL_METHOD,
    OperationalDataError,
    predict_outlet_sku,
)
from services.model_loader import get_model_artifacts
from services.runtime_readiness import require_runtime_readiness


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
        method: str = MODEL_METHOD,
        confidence: float = 0.0,
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


def _generate_forecast_run_id(db: Session, target_date: date) -> str:
    date_prefix = target_date.strftime("%Y%m%d")
    existing_count = db.query(ForecastRun).filter(ForecastRun.forecast_date == target_date).count()
    return f"fr_{date_prefix}_{existing_count + 1:03d}"


def _model_version() -> str:
    metrics = get_model_artifacts().metrics or {}
    return metrics.get("model_version") or MODEL_METHOD


def _model_confidence() -> float:
    metrics = get_model_artifacts().metrics or {}
    return float(metrics.get("band_coverage_p10_p90") or 0.0)


def _get_or_create_model_run(db: Session) -> ModelRun:
    artifacts = get_model_artifacts()
    artifacts.validate_for_inference()
    metrics = artifacts.metrics or {}
    artifact_version = metrics.get("model_version", MODEL_METHOD)

    latest = db.query(ModelRun).order_by(desc(ModelRun.created_at), desc(ModelRun.id)).first()
    if latest and latest.model_version == artifact_version and latest.engine_name == ENGINE_NAME:
        latest.metrics = metrics
        latest.status = "active"
        db.add(latest)
        db.flush()
        return latest

    model_run = ModelRun(
        model_version=artifact_version,
        engine_name=ENGINE_NAME,
        status="active",
        metrics=metrics,
    )
    db.add(model_run)
    db.flush()
    return model_run


def _rationale(prediction) -> dict:
    return {
        "model_version": _model_version(),
        "engine_name": ENGINE_NAME,
        "method": MODEL_METHOD,
        "reason_tags": ["LightGBM inference"],
        "uncertainty": {
            row.daypart: {
                "p10": row.p10,
                "p50": row.p50,
                "p90": row.p90,
                "source": row.uncertainty_source,
            }
            for row in prediction.dayparts
        },
        "feature_rows": {
            row.daypart: {
                "raw": row.raw_features,
                "encoded_feature_count": len(row.encoded_features),
            }
            for row in prediction.dayparts
        },
    }


def forecast_demand(
    outlet_id: int,
    sku_id: int,
    target_date: date,
    db: Session,
) -> ForecastResult:
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id, Outlet.is_active == True).first()
    sku = db.query(SKU).filter(SKU.id == sku_id, SKU.is_active == True).first()
    if not outlet:
        raise OperationalDataError(f"Outlet {outlet_id} is not active or does not exist")
    if not sku:
        raise OperationalDataError(f"SKU {sku_id} is not active or does not exist")

    prediction = predict_outlet_sku(db=db, outlet=outlet, sku=sku, target_date=target_date)
    return ForecastResult(
        outlet_id=outlet_id,
        sku_id=sku_id,
        target_date=target_date,
        morning=prediction.morning,
        midday=prediction.midday,
        evening=prediction.evening,
        total=prediction.total,
        method=MODEL_METHOD,
        confidence=_model_confidence(),
        rationale=_rationale(prediction),
    )


def run_forecast_for_date(target_date: date, db: Session) -> ForecastRun:
    require_runtime_readiness(target_date, db)
    model_run = _get_or_create_model_run(db)

    run = ForecastRun(
        forecast_run_id=_generate_forecast_run_id(db, target_date),
        forecast_date=target_date,
        model_run_id=model_run.id,
        status="completed",
        engine_name=ENGINE_NAME,
        model_version=model_run.model_version,
    )
    db.add(run)
    db.flush()

    outlets = db.query(Outlet).filter(Outlet.is_active == True).all()
    skus = db.query(SKU).filter(SKU.is_active == True).all()

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
