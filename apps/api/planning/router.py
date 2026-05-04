"""
Planning router — Task 10
GET  /api/daily-plan/{date}
POST /plans/prep/run
POST /plans/replenishment/run
"""
from datetime import date as date_type, datetime, timezone
from typing import Optional, Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import (
    DecisionAuditEvent,
    ForecastRun,
    Ingredient,
    Outlet,
    PrepPlan,
    PrepPlanLine,
    RecipeBOM,
    ReplenishmentPlan,
    SKU,
)
from planning.prep import generate_prep_plan
from planning.replenishment import recommend_replenishment
from forecasting.engine import run_forecast_for_date
from alerts.waste import detect_waste_risk
from alerts.stockout import detect_stockout_risk
from services.model_loader import load_model_for_inference

router = APIRouter()


# ─── Response schemas ─────────────────────────────────────────────────────────

class SummaryOut(BaseModel):
    total_predicted_sales: float
    waste_risk_score: int         # 0-100
    stockout_risk_score: int      # 0-100
    top_actions: list[str]
    at_risk_outlets: list[str]


class ForecastLineOut(BaseModel):
    outlet_id: int
    outlet_name: str
    sku_id: int
    sku_name: str
    morning: float
    midday: float
    evening: float
    total: float
    reason_tags: list[str]


class PrepLineOut(BaseModel):
    id: int
    outlet_id: int
    sku_id: int
    daypart: str
    recommended_units: int
    edited_units: Optional[int]
    current_stock: int
    status: str


class ReplenLineOut(BaseModel):
    ingredient_id: int
    ingredient_name: str
    need_qty: float
    stock_on_hand: float
    reorder_qty: float
    urgency: str
    driving_skus: list[str]


class AlertOut(BaseModel):
    outlet_name: str
    sku_name: str
    daypart: str
    risk_level: str
    reason: str


class DailyPlanOut(BaseModel):
    forecast_run_id: str
    model_run_id: Optional[int]
    model_version: str
    engine_name: str
    model_status: str
    validation_window: str
    metrics: Dict[str, Any]
    date: str
    prep_plan_id: Optional[int]
    replenishment_plan_id: Optional[int]
    forecasts: list[ForecastLineOut]
    prep_plan: list[PrepLineOut]
    replenishment_plan: list[ReplenLineOut]
    waste_alerts: list[AlertOut]
    stockout_alerts: list[AlertOut]
    summary: SummaryOut


class PlanRunOut(BaseModel):
    plan_id: int
    plan_date: str
    status: str
    lines_count: int


class FinancialExposureOut(BaseModel):
    stockout_exposure_rm: float
    waste_exposure_rm: float


class ReplenishmentItemOut(BaseModel):
    ingredient_id: str
    ingredient_name: str
    required_qty: float
    current_stock: float
    shortage_qty: float
    unit: str


class TopActionOut(BaseModel):
    id: str
    outlet_id: str
    outlet_name: str
    sku_id: str
    sku_name: str
    sku_category: str
    daypart: str
    p10: float
    p50: float
    p90: float
    opening_stock: float
    recommended_prep: int
    batch_size: int
    waste_cost: float
    stockout_cost: float
    financial_exposure: FinancialExposureOut
    reason_summary: str
    replenishment: list[ReplenishmentItemOut]
    status: str


class DailyPlanLatestOut(BaseModel):
    forecast_run_id: str
    model_run_id: str
    model_version: str
    engine_name: str
    model_status: str
    validation_window: str
    metrics: dict
    top_actions: list[TopActionOut]


class ForecastAdjustmentEntry(BaseModel):
    outlet_id: str
    daypart: str
    sku_category: str
    adjustment_pct: float
    reason: str


class ApplyAdjustmentRequest(BaseModel):
    forecast_run_id: str
    adjustment: ForecastAdjustmentEntry


class RecommendationDecisionRequest(BaseModel):
    operator_action: str
    final_prep: int
    operator_reason: str
    role: Optional[str] = "outlet_manager"


class RecommendationDecisionResponse(BaseModel):
    audit_event_id: int
    status: str
    final_prep: int


class PrepPlanLineContractOut(BaseModel):
    id: int
    outlet_id: int
    outlet_name: str
    sku_id: int
    sku_name: str
    sku_category: str
    daypart: str
    recommended_units: int
    edited_units: Optional[int]
    final_units: int
    current_stock: int
    status: str


class PrepPlanContractOut(BaseModel):
    id: int
    plan_date: str
    forecast_run_id: Optional[str]
    status: str
    approved_by: Optional[str]
    approved_at: Optional[str]
    lines: list[PrepPlanLineContractOut]


class PrepPlanEditRequest(BaseModel):
    line_id: int
    final_prep: int
    operator_reason: str
    user_id: str = "ops-manager"


class PrepPlanApproveRequest(BaseModel):
    approved_by: str = "ops-manager"
    operator_reason: Optional[str] = "Approved plan"


class PrepPlanRejectRequest(BaseModel):
    operator_reason: str
    rejected_by: str = "ops-manager"


class PrepPlanDecisionOut(BaseModel):
    plan_id: int
    status: str
    audit_event_ids: list[int]
    replenishment_plan_id: Optional[int]
    stock_warnings: list[str] = []


class ReplenishmentContractLineOut(BaseModel):
    ingredient_id: int
    ingredient_name: str
    required_qty: float
    current_stock: float
    shortage_qty: float
    reorder_qty: float
    unit: str
    urgency: str
    driving_skus: list[str]


class ReplenishmentContractOut(BaseModel):
    id: int
    plan_date: str
    status: str
    lines: list[ReplenishmentContractLineOut]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _score_risk(alerts: list, high_weight: int = 20, medium_weight: int = 8) -> int:
    score = 0
    for a in alerts:
        rl = getattr(a, "risk_level", "low")
        if rl == "high":
            score += high_weight
        elif rl == "medium":
            score += medium_weight
    return min(100, score)


def _build_top_actions(waste_alerts, stockout_alerts, repl_lines) -> list[str]:
    actions: list[str] = []
    seen_outlets: set = set()
    for a in waste_alerts[:3]:
        key = (a.outlet_name, a.sku_name)
        if key not in seen_outlets:
            actions.append(f"Reduce {a.sku_name} prep at {a.outlet_name} (waste risk {a.risk_level})")
            seen_outlets.add(key)
    for a in stockout_alerts[:2]:
        actions.append(f"Increase {a.sku_name} stock at {a.outlet_name} for {a.affected_daypart}")
    for r in repl_lines:
        if r.urgency in ("critical", "high") and len(actions) < 5:
            actions.append(f"Reorder {r.ingredient.name} – {r.urgency.upper()} urgency")
    return actions[:5]


def _latest_forecast_for_date(plan_date: date_type, db: Session) -> Optional[ForecastRun]:
    return (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_date == plan_date)
        .order_by(desc(ForecastRun.created_at), desc(ForecastRun.id))
        .first()
    )


def _latest_prep_plan(plan_date: Optional[date_type], db: Session) -> Optional[PrepPlan]:
    query = db.query(PrepPlan)
    if plan_date is not None:
        query = query.filter(PrepPlan.plan_date == plan_date)
    return query.order_by(desc(PrepPlan.created_at), desc(PrepPlan.id)).first()


def _latest_replenishment_plan(plan_date: Optional[date_type], db: Session) -> Optional[ReplenishmentPlan]:
    query = db.query(ReplenishmentPlan)
    if plan_date is not None:
        query = query.filter(ReplenishmentPlan.plan_date == plan_date)
    return query.order_by(desc(ReplenishmentPlan.created_at), desc(ReplenishmentPlan.id)).first()


def _serialize_prep_plan(plan: PrepPlan, db: Session, forecast_run: Optional[ForecastRun] = None) -> PrepPlanContractOut:
    outlets_map = {o.id: o.name for o in db.query(Outlet).all()}
    skus = {s.id: s for s in db.query(SKU).all()}
    if forecast_run is None:
        forecast_run = _latest_forecast_for_date(plan.plan_date, db)
    return PrepPlanContractOut(
        id=plan.id,
        plan_date=str(plan.plan_date),
        forecast_run_id=forecast_run.forecast_run_id if forecast_run else None,
        status=plan.status,
        approved_by=plan.approved_by,
        approved_at=plan.approved_at.isoformat() if plan.approved_at else None,
        lines=[
            PrepPlanLineContractOut(
                id=line.id,
                outlet_id=line.outlet_id,
                outlet_name=outlets_map.get(line.outlet_id, ""),
                sku_id=line.sku_id,
                sku_name=skus[line.sku_id].name if line.sku_id in skus else "",
                sku_category=skus[line.sku_id].category if line.sku_id in skus else "",
                daypart=line.daypart,
                recommended_units=line.recommended_units,
                edited_units=line.edited_units,
                final_units=line.edited_units if line.edited_units is not None else line.recommended_units,
                current_stock=line.current_stock,
                status=line.status,
            )
            for line in plan.lines
        ],
    )


def _serialize_replenishment_plan(plan: ReplenishmentPlan) -> ReplenishmentContractOut:
    return ReplenishmentContractOut(
        id=plan.id,
        plan_date=str(plan.plan_date),
        status=plan.status,
        lines=[
            ReplenishmentContractLineOut(
                ingredient_id=line.ingredient_id,
                ingredient_name=line.ingredient.name if line.ingredient else "",
                required_qty=round(line.need_qty, 3),
                current_stock=round(line.stock_on_hand, 3),
                shortage_qty=round(max(0.0, line.need_qty - line.stock_on_hand), 3),
                reorder_qty=round(line.reorder_qty, 3),
                unit=line.ingredient.unit if line.ingredient else "units",
                urgency=line.urgency,
                driving_skus=line.driving_skus or [],
            )
            for line in plan.lines
        ],
    )


def _refresh_replenishment(plan_date: date_type, db: Session) -> Optional[ReplenishmentPlan]:
    existing = (
        db.query(ReplenishmentPlan)
        .filter(ReplenishmentPlan.plan_date == plan_date)
        .all()
    )
    for plan in existing:
        db.delete(plan)
    db.commit()
    return recommend_replenishment(plan_date, db)


def _forecast_values_for_line(line: PrepPlanLine, db: Session) -> tuple[str, str, float, float, float]:
    forecast_run = _latest_forecast_for_date(line.plan.plan_date, db)
    if not forecast_run:
        return f"manual_{line.plan.plan_date.isoformat()}", "unknown", 0.0, float(line.recommended_units), float(line.recommended_units)
    matching = next(
        (
            candidate
            for candidate in forecast_run.lines
            if candidate.outlet_id == line.outlet_id and candidate.sku_id == line.sku_id
        ),
        None,
    )
    if not matching:
        p50 = float(line.recommended_units)
    else:
        p50 = float(getattr(matching, line.daypart, matching.total))
    return (
        forecast_run.forecast_run_id,
        forecast_run.model_version,
        round(max(0.0, p50 * 0.8), 2),
        round(p50, 2),
        round(max(p50, p50 * 1.25), 2),
    )


def _record_line_decision(
    line: PrepPlanLine,
    final_prep: int,
    operator_action: str,
    operator_reason: str,
    user_id: str,
    db: Session,
    gemini_note_adjustment_applied: bool = False,
    gemini_note_summary: Optional[str] = None,
) -> DecisionAuditEvent:
    forecast_run_id, model_version, p10, p50, p90 = _forecast_values_for_line(line, db)
    event = DecisionAuditEvent(
        forecast_run_id=forecast_run_id,
        model_version=model_version,
        engine_name="lightgbm_mlops_prototype" if model_version != "unknown" else "manual",
        outlet_id=line.outlet_id,
        sku_id=line.sku_id,
        daypart=line.daypart,
        p10=p10,
        p50=p50,
        p90=p90,
        recommended_prep=line.recommended_units,
        final_prep=final_prep,
        operator_action=operator_action,
        operator_reason=operator_reason,
        gemini_note_adjustment_applied=gemini_note_adjustment_applied,
        gemini_note_summary=gemini_note_summary,
    )
    db.add(event)
    db.flush()
    return event


def _apply_ingredient_stock_movement(plan: PrepPlan, db: Session) -> list[str]:
    sku_totals: dict[int, int] = {}
    for line in plan.lines:
        qty = line.edited_units if line.edited_units is not None else line.recommended_units
        sku_totals[line.sku_id] = sku_totals.get(line.sku_id, 0) + max(0, qty)

    warnings: list[str] = []
    for bom in db.query(RecipeBOM).all():
        used_qty = sku_totals.get(bom.sku_id, 0) * bom.quantity_per_unit
        if used_qty <= 0:
            continue
        ingredient = db.query(Ingredient).filter(Ingredient.id == bom.ingredient_id).first()
        if not ingredient:
            continue
        ingredient.stock_on_hand = round(ingredient.stock_on_hand - used_qty, 3)
        if ingredient.stock_on_hand < 0:
            warnings.append(
                f"{ingredient.name} stock is negative after approval ({ingredient.stock_on_hand} {ingredient.unit})."
            )
        db.add(ingredient)
    return warnings


# ─── Main daily plan endpoint ─────────────────────────────────────────────────

@router.get("/api/daily-plan/latest", response_model=DailyPlanOut)
def get_latest_daily_plan(date: Optional[date_type] = None, db: Session = Depends(get_db)):
    """Get or regenerate the latest daily plan for a given date."""
    if date is None:
        date = date_type.today()

    return _build_daily_plan_response(date, db)


@router.post("/api/daily-plan/regenerate")
def regenerate_daily_plan(date: date_type, reason: str = "manual_refresh", db: Session = Depends(get_db)):
    """Force regenerate the daily plan for a date."""
    # Delete existing runs/plans for this date
    db.query(ForecastRun).filter(ForecastRun.forecast_date == date).delete()
    db.query(PrepPlan).filter(PrepPlan.plan_date == date).delete()
    db.query(ReplenishmentPlan).filter(ReplenishmentPlan.plan_date == date).delete()
    db.commit()

    # Regenerate
    plan = _build_daily_plan_response(date, db)
    return {
        "forecast_run_id": plan.forecast_run_id,
        "status": "generated",
        "message": "Daily plan regenerated successfully.",
    }


def _build_daily_plan_response(plan_date: date_type, db: Session) -> DailyPlanOut:
    """Build full daily plan response with forecasts, prep, replenishment, alerts."""
    outlets_map = {o.id: o.name for o in db.query(Outlet).all()}
    skus_map = {s.id: s.name for s in db.query(SKU).all()}

    # Run or reuse forecast
    fc_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_date == plan_date)
        .order_by(desc(ForecastRun.created_at), desc(ForecastRun.id))
        .first()
    )
    if not fc_run:
        fc_run = run_forecast_for_date(plan_date, db)

    # Run or reuse prep plan
    prep_plan = (
        db.query(PrepPlan)
        .filter(PrepPlan.plan_date == plan_date)
        .order_by(desc(PrepPlan.created_at), desc(PrepPlan.id))
        .first()
    )
    if not prep_plan:
        prep_plan = generate_prep_plan(plan_date, db)

    # Run or reuse replenishment plan
    repl_plan = (
        db.query(ReplenishmentPlan)
        .filter(ReplenishmentPlan.plan_date == plan_date)
        .order_by(desc(ReplenishmentPlan.created_at), desc(ReplenishmentPlan.id))
        .first()
    )
    if not repl_plan:
        repl_plan = recommend_replenishment(plan_date, db)

    # Detect alerts
    waste_alerts = detect_waste_risk(plan_date, db)
    stockout_alerts = detect_stockout_risk(plan_date, db)

    # Get model info
    model_info = load_model_for_inference()
    model_run = fc_run.model_run

    # Build forecast lines
    forecast_lines = [
        ForecastLineOut(
            outlet_id=l.outlet_id,
            outlet_name=outlets_map.get(l.outlet_id, ""),
            sku_id=l.sku_id,
            sku_name=skus_map.get(l.sku_id, ""),
            morning=round(l.morning, 1),
            midday=round(l.midday, 1),
            evening=round(l.evening, 1),
            total=round(l.total, 1),
            reason_tags=(l.rationale_json or {}).get("reason_tags", []),
        )
        for l in fc_run.lines
    ]

    # Build prep plan lines
    prep_lines = [
        PrepLineOut(
            id=l.id,
            outlet_id=l.outlet_id,
            sku_id=l.sku_id,
            daypart=l.daypart,
            recommended_units=l.recommended_units,
            edited_units=l.edited_units,
            current_stock=l.current_stock,
            status=l.status,
        )
        for l in prep_plan.lines
    ]

    # Build replenishment lines
    repl_lines_out = [
        ReplenLineOut(
            ingredient_id=l.ingredient_id,
            ingredient_name=l.ingredient.name if l.ingredient else "",
            need_qty=round(l.need_qty, 2),
            stock_on_hand=round(l.stock_on_hand, 2),
            reorder_qty=round(l.reorder_qty, 2),
            urgency=l.urgency,
            driving_skus=l.driving_skus or [],
        )
        for l in repl_plan.lines
    ]

    # Summary
    total_sales = sum(l.total for l in fc_run.lines)
    waste_score = _score_risk(waste_alerts)
    stockout_score = _score_risk(stockout_alerts)

    actions = _build_top_actions(waste_alerts, stockout_alerts, repl_plan.lines)
    at_risk_outlets = list({a.outlet_name for a in (waste_alerts + stockout_alerts) if a.risk_level == "high"})

    summary = SummaryOut(
        total_predicted_sales=round(total_sales, 0),
        waste_risk_score=waste_score,
        stockout_risk_score=stockout_score,
        top_actions=actions,
        at_risk_outlets=at_risk_outlets[:5],
    )

    return DailyPlanOut(
        forecast_run_id=fc_run.forecast_run_id,
        model_run_id=model_run.id if model_run else None,
        model_version=model_run.model_version if model_run else "unknown",
        engine_name=fc_run.engine_name,
        model_status=model_info["model_status"],
        validation_window=model_info["validation_window"],
        metrics=model_info["metrics"],
        date=str(plan_date),
        prep_plan_id=prep_plan.id,
        replenishment_plan_id=repl_plan.id,
        forecasts=forecast_lines,
        prep_plan=prep_lines,
        replenishment_plan=repl_lines_out,
        waste_alerts=[
            AlertOut(
                outlet_name=a.outlet_name,
                sku_name=a.sku_name,
                daypart=a.daypart,
                risk_level=a.risk_level,
                reason=a.reason,
            )
            for a in waste_alerts
        ],
        stockout_alerts=[
            AlertOut(
                outlet_name=a.outlet_name,
                sku_name=a.sku_name,
                daypart=a.affected_daypart,
                risk_level=a.risk_level,
                reason=a.reason,
            )
            for a in stockout_alerts
        ],
        summary=summary,
    )


@router.get("/api/daily-plan/{plan_date}", response_model=DailyPlanOut)
def get_daily_plan(plan_date: date_type, db: Session = Depends(get_db)):
    """Get daily plan by date (alias for backward compatibility)."""
    return _build_daily_plan_response(plan_date, db)


@router.get("/prep-plans/latest", response_model=PrepPlanContractOut)
def get_latest_prep_plan(date: Optional[date_type] = None, db: Session = Depends(get_db)):
    plan = _latest_prep_plan(date, db)
    if not plan:
        target_date = date or date_type.today()
        plan = generate_prep_plan(target_date, db)
    return _serialize_prep_plan(plan, db)


@router.get("/prep-plans/{forecast_run_id}", response_model=PrepPlanContractOut)
def get_prep_plan_for_forecast(forecast_run_id: str, db: Session = Depends(get_db)):
    forecast_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_run_id == forecast_run_id)
        .first()
    )
    if not forecast_run and forecast_run_id.isdigit():
        forecast_run = db.query(ForecastRun).filter(ForecastRun.id == int(forecast_run_id)).first()
    if not forecast_run:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    plan = _latest_prep_plan(forecast_run.forecast_date, db)
    if not plan:
        plan = generate_prep_plan(forecast_run.forecast_date, db)
    return _serialize_prep_plan(plan, db, forecast_run)


@router.post("/prep-plans/{plan_id}/edit", response_model=PrepPlanDecisionOut)
def edit_contract_prep_plan(plan_id: int, body: PrepPlanEditRequest, db: Session = Depends(get_db)):
    if body.final_prep < 0:
        raise HTTPException(status_code=422, detail="final_prep must be >= 0")
    if not body.operator_reason.strip():
        raise HTTPException(status_code=422, detail="operator_reason is required")

    plan = db.query(PrepPlan).filter(PrepPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Prep plan not found")
    if plan.status == "approved":
        raise HTTPException(status_code=409, detail="Cannot edit an approved plan")
    line = (
        db.query(PrepPlanLine)
        .filter(PrepPlanLine.id == body.line_id, PrepPlanLine.plan_id == plan_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Prep plan line not found")

    line.edited_units = body.final_prep
    line.status = "edited"
    db.add(line)
    audit = _record_line_decision(
        line=line,
        final_prep=body.final_prep,
        operator_action="edited",
        operator_reason=body.operator_reason,
        user_id=body.user_id,
        db=db,
    )
    db.commit()
    replenishment_plan = _refresh_replenishment(plan.plan_date, db)
    return PrepPlanDecisionOut(
        plan_id=plan.id,
        status="edited",
        audit_event_ids=[audit.id],
        replenishment_plan_id=replenishment_plan.id if replenishment_plan else None,
    )


@router.post("/prep-plans/{plan_id}/approve", response_model=PrepPlanDecisionOut)
def approve_contract_prep_plan(plan_id: int, body: PrepPlanApproveRequest, db: Session = Depends(get_db)):
    plan = db.query(PrepPlan).filter(PrepPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Prep plan not found")
    if plan.status == "approved":
        raise HTTPException(status_code=409, detail="Plan is already approved")

    audit_ids: list[int] = []
    for line in plan.lines:
        final_units = line.edited_units if line.edited_units is not None else line.recommended_units
        line.status = "accepted" if line.status == "pending" else line.status
        db.add(line)
        audit = _record_line_decision(
            line=line,
            final_prep=final_units,
            operator_action="approved",
            operator_reason=body.operator_reason or "Approved plan",
            user_id=body.approved_by,
            db=db,
        )
        audit_ids.append(audit.id)

    plan.status = "approved"
    plan.approved_by = body.approved_by
    plan.approved_at = datetime.now(timezone.utc)
    stock_warnings = _apply_ingredient_stock_movement(plan, db)
    db.add(plan)
    db.commit()
    replenishment_plan = _refresh_replenishment(plan.plan_date, db)
    return PrepPlanDecisionOut(
        plan_id=plan.id,
        status=plan.status,
        audit_event_ids=audit_ids,
        replenishment_plan_id=replenishment_plan.id if replenishment_plan else None,
        stock_warnings=stock_warnings,
    )


@router.post("/prep-plans/{plan_id}/reject", response_model=PrepPlanDecisionOut)
def reject_contract_prep_plan(plan_id: int, body: PrepPlanRejectRequest, db: Session = Depends(get_db)):
    if not body.operator_reason.strip():
        raise HTTPException(status_code=422, detail="operator_reason is required")
    plan = db.query(PrepPlan).filter(PrepPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Prep plan not found")
    if plan.status == "approved":
        raise HTTPException(status_code=409, detail="Cannot reject an approved plan")

    audit_ids: list[int] = []
    for line in plan.lines:
        final_units = line.edited_units if line.edited_units is not None else line.recommended_units
        line.status = "rejected"
        db.add(line)
        audit = _record_line_decision(
            line=line,
            final_prep=final_units,
            operator_action="rejected",
            operator_reason=body.operator_reason,
            user_id=body.rejected_by,
            db=db,
        )
        audit_ids.append(audit.id)
    plan.status = "rejected"
    db.add(plan)
    db.commit()
    return PrepPlanDecisionOut(
        plan_id=plan.id,
        status=plan.status,
        audit_event_ids=audit_ids,
        replenishment_plan_id=None,
    )


@router.get("/replenishment/latest", response_model=ReplenishmentContractOut)
def get_latest_replenishment(date: Optional[date_type] = None, db: Session = Depends(get_db)):
    target_date = date or date_type.today()
    plan = _latest_replenishment_plan(target_date, db)
    if not plan:
        if not _latest_prep_plan(target_date, db):
            generate_prep_plan(target_date, db)
        plan = recommend_replenishment(target_date, db)
    return _serialize_replenishment_plan(plan)


@router.post(
    "/api/daily-plan/recommendations/{recommendation_id}/decision",
    response_model=RecommendationDecisionResponse,
)
def apply_recommendation_decision(
    recommendation_id: int,
    decision: RecommendationDecisionRequest,
    db: Session = Depends(get_db),
):
    """
    Apply a manager decision to a prep recommendation.
    operator_action: approved | edited | rejected
    """
    from db.models import PrepPlanLine

    line = db.query(PrepPlanLine).filter(PrepPlanLine.id == recommendation_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # Update line
    line.edited_units = decision.final_prep
    line.status = (
        "accepted"
        if decision.operator_action == "approved"
        else "edited"
        if decision.operator_action == "edited"
        else "rejected"
    )
    db.add(line)
    db.flush()

    audit_event = _record_line_decision(
        line=line,
        final_prep=decision.final_prep,
        operator_action=decision.operator_action,
        operator_reason=decision.operator_reason,
        user_id=decision.role,
        db=db,
    )

    db.commit()

    return RecommendationDecisionResponse(
        audit_event_id=audit_event.id,
        status="recorded",
        final_prep=decision.final_prep,
    )


# ─── Trigger endpoints ────────────────────────────────────────────────────────

@router.post("/plans/prep/run", response_model=PlanRunOut)
def run_prep_plan(target_date: date_type = None, db: Session = Depends(get_db)):
    if target_date is None:
        target_date = date_type.today()
    plan = generate_prep_plan(target_date, db)
    return PlanRunOut(
        plan_id=plan.id,
        plan_date=str(plan.plan_date),
        status=plan.status,
        lines_count=len(plan.lines),
    )


@router.post("/plans/replenishment/run", response_model=PlanRunOut)
def run_replenishment_plan(target_date: date_type = None, db: Session = Depends(get_db)):
    if target_date is None:
        target_date = date_type.today()
    plan = recommend_replenishment(target_date, db)
    return PlanRunOut(
        plan_id=plan.id,
        plan_date=str(plan.plan_date),
        status=plan.status,
        lines_count=len(plan.lines),
    )
