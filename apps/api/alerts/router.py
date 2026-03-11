"""
Alerts router + Planning router — Tasks 8, 9, 10
GET  /alerts/waste?date=
GET  /alerts/stockout?date=
GET  /api/daily-plan/{date}
POST /plans/prep/run
POST /plans/replenishment/run
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from alerts.waste import detect_waste_risk, WasteAlert
from alerts.stockout import detect_stockout_risk, StockoutAlert

router = APIRouter()


class WasteAlertOut(BaseModel):
    outlet_id: int
    outlet_name: str
    sku_id: int
    sku_name: str
    daypart: str
    risk_level: str
    triggers: list[str]
    reason: str
    waste_rate: float
    excess_prep_units: float


class StockoutAlertOut(BaseModel):
    outlet_id: int
    outlet_name: str
    sku_id: int
    sku_name: str
    affected_daypart: str
    risk_level: str
    shortage_qty: float
    reason: str
    coverage_pct: float


@router.get("/alerts/waste", response_model=list[WasteAlertOut])
def get_waste_alerts(
    target_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    if target_date is None:
        target_date = date.today()
    alerts = detect_waste_risk(target_date, db)
    return [WasteAlertOut(**a.__dict__) for a in alerts]


@router.get("/alerts/stockout", response_model=list[StockoutAlertOut])
def get_stockout_alerts(
    target_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    if target_date is None:
        target_date = date.today()
    alerts = detect_stockout_risk(target_date, db)
    return [StockoutAlertOut(**a.__dict__) for a in alerts]
