"""
Forecast runs service — manages saved forecast runs
"""
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.models import ForecastRun, ForecastLine, ModelRun, Outlet, SKU
from services.model_loader import load_model_for_inference


def get_or_create_model_run(db: Session) -> ModelRun:
    """Get the latest model run or create a placeholder"""
    latest = db.query(ModelRun).order_by(desc(ModelRun.created_at)).first()
    if latest:
        return latest

    # Create placeholder model run
    model_run = ModelRun(
        model_version="lightgbm_p50_v1",
        engine_name="lightgbm_mlops_prototype",
        status="active",
        metrics={"placeholder": True},
    )
    db.add(model_run)
    db.flush()
    return model_run


def generate_forecast_run(
    target_date: date,
    db: Session,
    features_df=None,  # Would come from ML pipeline
) -> ForecastRun:
    """
    Generate and save a forecast run.

    In production, this would:
    1. Load latest features
    2. Predict p50 using model
    3. Apply residual bands for p10/p90
    4. Save forecast_run and forecast_lines
    """
    # For now, create a placeholder forecast run
    # This should be replaced with actual ML pipeline integration

    model_info = load_model_for_inference()
    model_run = get_or_create_model_run(db)

    forecast_run = ForecastRun(
        forecast_date=target_date,
        model_run_id=model_run.id,
        status="completed",
        engine_name=model_info["engine_name"],
        model_version=model_run.model_version,
    )
    db.add(forecast_run)
    db.flush()

    # Placeholder forecast lines - replace with actual predictions
    # This is just for structure; actual implementation needs ML integration
    outlets = db.query(Outlet).filter(Outlet.is_active == True).all()
    skus = db.query(SKU).filter(SKU.is_active == True).all()

    for outlet in outlets:
        for sku in skus:
            # Dummy predictions - replace with real ML
            line = ForecastLine(
                run_id=forecast_run.id,
                outlet_id=outlet.id,
                sku_id=sku.id,
                p10=80,  # Placeholder
                p50=100,  # Placeholder
                p90=125,  # Placeholder
                method="placeholder",
                confidence=0.8,
            )
            db.add(line)

    db.commit()
    db.refresh(forecast_run)
    return forecast_run


def get_latest_forecast_run(target_date: date, db: Session) -> Optional[ForecastRun]:
    """Get the latest forecast run for a date"""
    return (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_date == target_date)
        .order_by(desc(ForecastRun.created_at))
        .first()
    )


def get_forecast_run_by_id(run_id: int, db: Session) -> Optional[ForecastRun]:
    """Get forecast run by ID"""
    return db.query(ForecastRun).filter(ForecastRun.id == run_id).first()