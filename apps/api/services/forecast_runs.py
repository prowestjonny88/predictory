"""Saved forecast-run helpers backed by the active forecasting engine."""
from datetime import date
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from db.models import ForecastRun
from forecasting.engine import run_forecast_for_date


def generate_forecast_run(target_date: date, db: Session) -> ForecastRun:
    """Generate and persist a versioned forecast run for a date."""
    return run_forecast_for_date(target_date, db)


def get_latest_forecast_run(target_date: Optional[date], db: Session) -> Optional[ForecastRun]:
    query = db.query(ForecastRun)
    if target_date is not None:
        query = query.filter(ForecastRun.forecast_date == target_date)
    return query.order_by(desc(ForecastRun.created_at), desc(ForecastRun.id)).first()


def get_forecast_run_by_public_id(forecast_run_id: str, db: Session) -> Optional[ForecastRun]:
    return db.query(ForecastRun).filter(ForecastRun.forecast_run_id == forecast_run_id).first()


def get_forecast_run_by_any_id(run_id: str, db: Session) -> Optional[ForecastRun]:
    if run_id.isdigit():
        run = db.query(ForecastRun).filter(ForecastRun.id == int(run_id)).first()
        if run:
            return run
    return get_forecast_run_by_public_id(run_id, db)
