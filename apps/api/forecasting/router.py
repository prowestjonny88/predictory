"""
Forecasting router - Task 5 + demand drivers
GET    /forecasts
POST   /forecasts/run
PATCH  /forecasts/{run_id}/lines/{line_id}
GET    /forecast-context
GET    /forecast-overrides
POST   /forecast-overrides
PATCH  /forecast-overrides/{override_id}
DELETE /forecast-overrides/{override_id}
"""
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import AuditEvent, ForecastLine, ForecastOverride, ForecastRun, Outlet, SKU
from forecasting.context import build_forecast_context
from forecasting.engine import run_forecast_for_date

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
    manual_adjustment_pct: float = Field(ge=-100)
    user_id: Optional[str] = "system"


class ForecastSignalOut(BaseModel):
    label: str
    source: str
    status: str
    adjustment_pct: float
    details: list[str]


class StockoutCensoringOut(BaseModel):
    enabled: bool
    adjusted_history_days: int
    adjusted_dates: list[str]
    note: str


class ForecastOverrideOut(BaseModel):
    id: int
    target_date: str
    outlet_id: int
    sku_id: Optional[int]
    sku_name: Optional[str]
    override_type: str
    title: str
    notes: Optional[str]
    adjustment_pct: float
    enabled: bool
    created_by: Optional[str]


class ForecastContextOut(BaseModel):
    target_date: str
    outlet_id: int
    sku_id: Optional[int]
    holiday: Optional[ForecastSignalOut]
    weather: ForecastSignalOut
    stockout_censoring: StockoutCensoringOut
    active_overrides: list[ForecastOverrideOut]
    combined_adjustment_pct: float


class ForecastOverrideCreate(BaseModel):
    target_date: date
    outlet_id: int
    sku_id: Optional[int] = None
    override_type: Literal["event", "promo"]
    title: str = Field(min_length=1, max_length=255)
    notes: Optional[str] = None
    adjustment_pct: float = Field(ge=-50, le=100)
    enabled: bool = True
    created_by: Optional[str] = "planner"


class ForecastOverrideUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    notes: Optional[str] = None
    adjustment_pct: Optional[float] = Field(default=None, ge=-50, le=100)
    enabled: Optional[bool] = None


def _serialize_override(override: ForecastOverride) -> ForecastOverrideOut:
    return ForecastOverrideOut(
        id=override.id,
        target_date=str(override.target_date),
        outlet_id=override.outlet_id,
        sku_id=override.sku_id,
        sku_name=override.sku.name if override.sku else None,
        override_type=override.override_type,
        title=override.title,
        notes=override.notes,
        adjustment_pct=override.adjustment_pct,
        enabled=override.enabled,
        created_by=override.created_by,
    )


def _require_outlet_and_sku(db: Session, outlet_id: int, sku_id: Optional[int] = None) -> tuple[Outlet, Optional[SKU]]:
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
    sku = None
    if sku_id is not None:
        sku = db.query(SKU).filter(SKU.id == sku_id).first()
        if not sku:
            raise HTTPException(status_code=404, detail="SKU not found")
    return outlet, sku


@router.post("/forecasts/run", response_model=ForecastRunOut)
def trigger_forecast(
    target_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    if target_date is None:
        from datetime import date as date_mod

        target_date = date_mod.today()
    return run_forecast_for_date(target_date, db)


@router.get("/forecasts", response_model=list[ForecastRunOut])
def get_forecasts(
    forecast_date: Optional[date] = Query(None),
    outlet_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(ForecastRun)
    if forecast_date:
        query = query.filter(ForecastRun.forecast_date == forecast_date)
    runs = query.order_by(ForecastRun.created_at.desc()).limit(10).all()

    if outlet_id:
        for run in runs:
            run.lines = [line for line in run.lines if line.outlet_id == outlet_id]

    return runs


@router.patch("/forecasts/{run_id}/lines/{line_id}", response_model=ForecastLineOut)
def adjust_forecast_line(
    run_id: int,
    line_id: int,
    body: AdjustmentRequest,
    db: Session = Depends(get_db),
):
    line = (
        db.query(ForecastLine)
        .filter(ForecastLine.id == line_id, ForecastLine.run_id == run_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="ForecastLine not found")

    before_value = {
        "morning": line.morning,
        "midday": line.midday,
        "evening": line.evening,
        "total": line.total,
        "manual_adjustment_pct": line.manual_adjustment_pct,
    }

    adjustment = body.manual_adjustment_pct / 100.0
    line.morning = round(line.morning * (1 + adjustment), 1)
    line.midday = round(line.midday * (1 + adjustment), 1)
    line.evening = round(line.evening * (1 + adjustment), 1)
    line.total = line.morning + line.midday + line.evening
    line.manual_adjustment_pct = body.manual_adjustment_pct

    db.add(
        AuditEvent(
            event_type="forecast_line_adjusted",
            entity_type="ForecastLine",
            entity_id=line.id,
            before_value=before_value,
            after_value={
                "morning": line.morning,
                "midday": line.midday,
                "evening": line.evening,
                "total": line.total,
                "manual_adjustment_pct": line.manual_adjustment_pct,
            },
            user_id=body.user_id,
        )
    )
    db.commit()
    db.refresh(line)
    return line


@router.get("/forecast-context", response_model=ForecastContextOut)
def get_forecast_context(
    target_date: date,
    outlet_id: int,
    sku_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    _require_outlet_and_sku(db, outlet_id, sku_id)
    context = build_forecast_context(
        outlet_id=outlet_id,
        sku_id=sku_id,
        target_date=target_date,
        db=db,
    )
    return ForecastContextOut(
        target_date=context["target_date"],
        outlet_id=context["outlet_id"],
        sku_id=context["sku_id"],
        holiday=context["holiday"],
        weather=context["weather"],
        stockout_censoring=context["stockout_censoring"],
        active_overrides=[ForecastOverrideOut(**payload) for payload in context["active_overrides"]],
        combined_adjustment_pct=context["combined_adjustment_pct"],
    )


@router.get("/forecast-overrides", response_model=list[ForecastOverrideOut])
def list_forecast_overrides(
    target_date: date,
    outlet_id: int,
    sku_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    _require_outlet_and_sku(db, outlet_id, sku_id)
    query = (
        db.query(ForecastOverride)
        .filter(
            ForecastOverride.target_date == target_date,
            ForecastOverride.outlet_id == outlet_id,
        )
        .order_by(ForecastOverride.created_at.desc())
    )
    if sku_id is not None:
        query = query.filter((ForecastOverride.sku_id == sku_id) | (ForecastOverride.sku_id.is_(None)))
    return [_serialize_override(override) for override in query.all()]


@router.post("/forecast-overrides", response_model=ForecastOverrideOut)
def create_forecast_override(body: ForecastOverrideCreate, db: Session = Depends(get_db)):
    _require_outlet_and_sku(db, body.outlet_id, body.sku_id)

    override = ForecastOverride(
        target_date=body.target_date,
        outlet_id=body.outlet_id,
        sku_id=body.sku_id,
        override_type=body.override_type,
        title=body.title,
        notes=body.notes,
        adjustment_pct=body.adjustment_pct,
        enabled=body.enabled,
        created_by=body.created_by,
    )
    db.add(override)
    db.flush()
    db.add(
        AuditEvent(
            event_type="forecast_override_created",
            entity_type="ForecastOverride",
            entity_id=override.id,
            before_value=None,
            after_value={
                "target_date": str(override.target_date),
                "outlet_id": override.outlet_id,
                "sku_id": override.sku_id,
                "override_type": override.override_type,
                "title": override.title,
                "adjustment_pct": override.adjustment_pct,
                "enabled": override.enabled,
            },
            user_id=body.created_by,
        )
    )
    db.commit()
    db.refresh(override)
    return _serialize_override(override)


@router.patch("/forecast-overrides/{override_id}", response_model=ForecastOverrideOut)
def update_forecast_override(override_id: int, body: ForecastOverrideUpdate, db: Session = Depends(get_db)):
    override = db.query(ForecastOverride).filter(ForecastOverride.id == override_id).first()
    if not override:
        raise HTTPException(status_code=404, detail="Forecast override not found")

    before_value = {
        "title": override.title,
        "notes": override.notes,
        "adjustment_pct": override.adjustment_pct,
        "enabled": override.enabled,
    }

    if body.title is not None:
        override.title = body.title
    if body.notes is not None:
        override.notes = body.notes
    if body.adjustment_pct is not None:
        override.adjustment_pct = body.adjustment_pct
    if body.enabled is not None:
        override.enabled = body.enabled

    db.add(
        AuditEvent(
            event_type="forecast_override_updated",
            entity_type="ForecastOverride",
            entity_id=override.id,
            before_value=before_value,
            after_value={
                "title": override.title,
                "notes": override.notes,
                "adjustment_pct": override.adjustment_pct,
                "enabled": override.enabled,
            },
            user_id=override.created_by,
        )
    )
    db.commit()
    db.refresh(override)
    return _serialize_override(override)


@router.delete("/forecast-overrides/{override_id}", status_code=204)
def delete_forecast_override(override_id: int, db: Session = Depends(get_db)):
    override = db.query(ForecastOverride).filter(ForecastOverride.id == override_id).first()
    if not override:
        raise HTTPException(status_code=404, detail="Forecast override not found")

    db.add(
        AuditEvent(
            event_type="forecast_override_deleted",
            entity_type="ForecastOverride",
            entity_id=override.id,
            before_value={
                "target_date": str(override.target_date),
                "outlet_id": override.outlet_id,
                "sku_id": override.sku_id,
                "override_type": override.override_type,
                "title": override.title,
                "adjustment_pct": override.adjustment_pct,
                "enabled": override.enabled,
            },
            after_value=None,
            user_id=override.created_by,
        )
    )
    db.delete(override)
    db.commit()
    return Response(status_code=204)
