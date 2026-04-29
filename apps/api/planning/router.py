"""
Planning router — Task 10
GET  /api/daily-plan/{date}
POST /plans/prep/run
POST /plans/replenishment/run
"""
from datetime import date as date_type
from typing import Optional, Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import (
    ForecastRun,
    Outlet,
    PrepPlan,
    ReplenishmentPlan,
    SKU,
)
from planning.prep import generate_prep_plan
from planning.replenishment import recommend_replenishment
from forecasting.engine import run_forecast_for_date
from alerts.waste import detect_waste_risk
from alerts.stockout import detect_stockout_risk
from services.model_loader import load_model_for_inference
from services.audit import log_decision_audit

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
        .order_by(ForecastRun.created_at.desc())
        .first()
    )
    if not fc_run:
        fc_run = run_forecast_for_date(plan_date, db)

    # Run or reuse prep plan
    prep_plan = (
        db.query(PrepPlan)
        .filter(PrepPlan.plan_date == plan_date)
        .order_by(PrepPlan.created_at.desc())
        .first()
    )
    if not prep_plan:
        prep_plan = generate_prep_plan(plan_date, db)

    # Run or reuse replenishment plan
    repl_plan = (
        db.query(ReplenishmentPlan)
        .filter(ReplenishmentPlan.plan_date == plan_date)
        .order_by(ReplenishmentPlan.created_at.desc())
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
    old_recommended = line.recommended_units
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

    forecast_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_date == line.plan.plan_date)
        .order_by(ForecastRun.created_at.desc())
        .first()
    )
    forecast_run_id = (
        forecast_run.forecast_run_id
        if forecast_run
        else f"manual_{line.plan.plan_date.isoformat()}"
    )

    audit_event = log_decision_audit(
        forecast_run_id=forecast_run_id,
        model_version=forecast_run.model_version if forecast_run else "unknown",
        engine_name=forecast_run.engine_name if forecast_run else "manual",
        outlet_id=line.outlet_id,
        sku_id=line.sku_id,
        daypart=line.daypart,
        p10=0.0,
        p50=float(old_recommended),
        p90=0.0,
        recommended_prep=old_recommended,
        final_prep=decision.final_prep,
        operator_action=decision.operator_action,
        operator_reason=decision.operator_reason,
        gemini_note_adjustment_applied=False,
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
