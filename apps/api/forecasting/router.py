"""
Forecasting router — Task 5
GET  /forecasts?date=YYYY-MM-DD
POST /forecasts/run
PATCH /forecasts/{run_id}/lines/{line_id}  (Task 27 — adjustment)
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import ForecastRun, ForecastLine
from forecasting.engine import run_forecast_for_date, forecast_demand

router = APIRouter()


class ForecastLineOut(BaseModel):
    id: int
    outlet_id: int
    sku_id: int
    morning: float
    midday: float
    evening: float
    total: float
    method: str
    confidence: float
    manual_adjustment_pct: Optional[float]
    rationale_json: Optional[dict]
    model_config = {"from_attributes": True}


class ForecastRunOut(BaseModel):
    id: int
    forecast_date: date
    status: str
    lines: list[ForecastLineOut]
    model_config = {"from_attributes": True}


class AdjustmentRequest(BaseModel):
    manual_adjustment_pct: float  # e.g. 10 means +10%, -15 means -15%


@router.post("/forecasts/run", response_model=ForecastRunOut)
def trigger_forecast(
    target_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    if target_date is None:
        from datetime import date as dmod
        target_date = dmod.today()
    run = run_forecast_for_date(target_date, db)
    return run


@router.get("/forecasts", response_model=list[ForecastRunOut])
def get_forecasts(
    forecast_date: Optional[date] = Query(None),
    outlet_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(ForecastRun)
    if forecast_date:
        q = q.filter(ForecastRun.forecast_date == forecast_date)
    runs = q.order_by(ForecastRun.created_at.desc()).limit(10).all()

    if outlet_id:
        for run in runs:
            run.lines = [l for l in run.lines if l.outlet_id == outlet_id]

    return runs


@router.patch("/forecasts/{run_id}/lines/{line_id}", response_model=ForecastLineOut)
def adjust_forecast_line(
    run_id: int,
    line_id: int,
    body: AdjustmentRequest,
    db: Session = Depends(get_db),
):
    line = db.query(ForecastLine).filter(
        ForecastLine.id == line_id,
        ForecastLine.run_id == run_id,
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="ForecastLine not found")

    adj = body.manual_adjustment_pct / 100.0
    line.morning = round(line.morning * (1 + adj), 1)
    line.midday = round(line.midday * (1 + adj), 1)
    line.evening = round(line.evening * (1 + adj), 1)
    line.total = line.morning + line.midday + line.evening
    line.manual_adjustment_pct = body.manual_adjustment_pct
    db.commit()
    db.refresh(line)
    return line
