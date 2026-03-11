"""
Planning router — Task 10
GET  /api/daily-plan/{date}
POST /plans/prep/run
POST /plans/replenishment/run
"""
from datetime import date as date_type
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import PrepPlan, ReplenishmentPlan, Outlet, SKU
from planning.prep import generate_prep_plan
from planning.replenishment import recommend_replenishment
from forecasting.engine import run_forecast_for_date
from alerts.waste import detect_waste_risk
from alerts.stockout import detect_stockout_risk

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

@router.get("/api/daily-plan/{plan_date}", response_model=DailyPlanOut)
def get_daily_plan(plan_date: date_type, db: Session = Depends(get_db)):
    outlets_map = {o.id: o.name for o in db.query(Outlet).all()}
    skus_map    = {s.id: s.name for s in db.query(SKU).all()}

    # Run or reuse forecast
    from db.models import ForecastRun
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
    waste_alerts    = detect_waste_risk(plan_date, db)
    stockout_alerts = detect_stockout_risk(plan_date, db)

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
            need_qty=l.need_qty,
            stock_on_hand=l.stock_on_hand,
            reorder_qty=l.reorder_qty,
            urgency=l.urgency,
            driving_skus=l.driving_skus or [],
        )
        for l in repl_plan.lines
    ]

    # Summary
    total_sales = sum(l.total for l in fc_run.lines)
    waste_score    = _score_risk(waste_alerts)
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
        date=str(plan_date),
        prep_plan_id=prep_plan.id,
        replenishment_plan_id=repl_plan.id,
        forecasts=forecast_lines,
        prep_plan=prep_lines,
        replenishment_plan=repl_lines_out,
        waste_alerts=[AlertOut(outlet_name=a.outlet_name, sku_name=a.sku_name, daypart=a.daypart, risk_level=a.risk_level, reason=a.reason) for a in waste_alerts],
        stockout_alerts=[AlertOut(outlet_name=a.outlet_name, sku_name=a.sku_name, daypart=a.affected_daypart, risk_level=a.risk_level, reason=a.reason) for a in stockout_alerts],
        summary=summary,
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
