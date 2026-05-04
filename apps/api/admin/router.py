"""Admin model registry endpoints."""
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ModelRun
from services.model_loader import load_model_for_inference

router = APIRouter()


class ModelRunOut(BaseModel):
    id: int
    model_version: str
    engine_name: str
    status: str
    validation_window: str
    artifact_loaded: bool
    metrics: dict
    created_at: datetime
    model_config = {"from_attributes": True}


class TrainModelOut(BaseModel):
    model_run_id: int
    status: str
    message: str
    model: ModelRunOut


def _normalize_metrics(metrics: dict) -> dict:
    validation_metrics = metrics.get("validation_metrics") or {}
    return {
        **metrics,
        "wape": validation_metrics.get("wape"),
        "bias": validation_metrics.get("bias"),
        "p10_p90_coverage": metrics.get("band_coverage_p10_p90"),
    }


def _model_run_out(model_run: ModelRun, artifact_loaded: bool, validation_window: str) -> ModelRunOut:
    return ModelRunOut(
        id=model_run.id,
        model_version=model_run.model_version,
        engine_name=model_run.engine_name,
        status=model_run.status,
        validation_window=validation_window,
        artifact_loaded=artifact_loaded,
        metrics=_normalize_metrics(model_run.metrics or {}),
        created_at=model_run.created_at,
    )


def _sync_artifact_model_run(db: Session, status: str = "active") -> ModelRun:
    model_info = load_model_for_inference()
    metrics = model_info.get("metrics") or {}
    model_version = metrics.get("model_version", "lightgbm_p50_v1")
    engine_name = model_info.get("engine_name", "baseline_heuristic")

    model_run = (
        db.query(ModelRun)
        .filter(ModelRun.model_version == model_version)
        .order_by(desc(ModelRun.created_at))
        .first()
    )
    if model_run:
        model_run.engine_name = engine_name
        model_run.status = status
        model_run.metrics = metrics
    else:
        model_run = ModelRun(
            model_version=model_version,
            engine_name=engine_name,
            status=status,
            metrics=metrics,
        )
    db.add(model_run)
    db.commit()
    db.refresh(model_run)
    return model_run


def _require_admin_token(authorization: Optional[str]) -> None:
    expected = os.getenv("ADMIN_API_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_API_TOKEN is not configured")
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != expected:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@router.get("/admin/models/latest", response_model=ModelRunOut)
def get_latest_model(db: Session = Depends(get_db)):
    model_run = _sync_artifact_model_run(db)
    model_info = load_model_for_inference()
    return _model_run_out(
        model_run,
        artifact_loaded=bool(model_info.get("is_loaded")),
        validation_window=model_info.get("validation_window", "unknown"),
    )


@router.get("/admin/models/{model_run_id}", response_model=ModelRunOut)
def get_model_run(model_run_id: int, db: Session = Depends(get_db)):
    model_run = db.query(ModelRun).filter(ModelRun.id == model_run_id).first()
    if not model_run:
        raise HTTPException(status_code=404, detail="Model run not found")
    model_info = load_model_for_inference()
    return _model_run_out(
        model_run,
        artifact_loaded=bool(model_info.get("is_loaded")),
        validation_window=(model_run.metrics or {}).get("validation_window", model_info.get("validation_window", "unknown")),
    )


@router.post("/admin/models/train", response_model=TrainModelOut)
def train_model_stub(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    _require_admin_token(authorization)
    model_run = _sync_artifact_model_run(db, status="manual_artifact_registered")
    model_info = load_model_for_inference()
    return TrainModelOut(
        model_run_id=model_run.id,
        status=model_run.status,
        message="Accepted ML artifacts registered. Retraining is intentionally not run by this demo endpoint.",
        model=_model_run_out(
            model_run,
            artifact_loaded=bool(model_info.get("is_loaded")),
            validation_window=model_info.get("validation_window", "unknown"),
        ),
    )
