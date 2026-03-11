"""
Copilot router — Task 18 + Task 21
POST /copilot/explain-plan
POST /copilot/daily-brief
POST /copilot/run-scenario
"""
import os
from datetime import date as date_type
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import Outlet, SKU, PrepPlan, ForecastRun
from copilot.prompts import (
    FORECAST_EXPLANATION_PROMPT,
    PREP_RATIONALE_PROMPT,
    DAILY_BRIEF_PROMPT,
    WASTE_ALERT_EXPLANATION_PROMPT,
    STOCKOUT_ALERT_EXPLANATION_PROMPT,
    REPLENISHMENT_RATIONALE_PROMPT,
)
from copilot.scenario import run_scenario_simulation

router = APIRouter()


# ─── LiteLLM wrapper ──────────────────────────────────────────────────────────

def _call_llm(prompt: str, fallback: str = "") -> str:
    """
    Call LiteLLM. Returns fallback string if LLM is unavailable.
    All data is injected into the prompt — the LLM never invents numbers.
    """
    try:
        import litellm
        model = os.getenv("LITELLM_MODEL", "gpt-4o-mini")
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return fallback or f"Explanation unavailable: {exc}"


# ─── Request/response schemas ─────────────────────────────────────────────────

class ExplainPlanRequest(BaseModel):
    outlet_id: int
    sku_id: int
    plan_date: date_type
    context_type: str = "forecast"  # forecast | prep | waste | stockout | replenishment


class ExplainPlanResponse(BaseModel):
    explanation: str
    context_type: str
    outlet_name: str
    sku_name: str


class DailyBriefRequest(BaseModel):
    brief_date: date_type


class DailyBriefResponse(BaseModel):
    brief: str
    date: str


class ScenarioRequest(BaseModel):
    scenario_text: str
    target_date: Optional[date_type] = None


class ScenarioResponse(BaseModel):
    scenario: str
    baseline: dict
    modified: dict
    delta: dict
    recommendation: str
    interpretation: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/copilot/explain-plan", response_model=ExplainPlanResponse)
def explain_plan(body: ExplainPlanRequest, db: Session = Depends(get_db)):
    outlet = db.query(Outlet).filter(Outlet.id == body.outlet_id).first()
    sku    = db.query(SKU).filter(SKU.id == body.sku_id).first()
    if not outlet or not sku:
        raise HTTPException(status_code=404, detail="Outlet or SKU not found")

    ctx = body.context_type

    # Build context-specific prompt
    if ctx == "forecast":
        fc_run = (
            db.query(ForecastRun)
            .filter(ForecastRun.forecast_date == body.plan_date)
            .order_by(ForecastRun.created_at.desc())
            .first()
        )
        line = next((l for l in (fc_run.lines if fc_run else [])
                     if l.outlet_id == body.outlet_id and l.sku_id == body.sku_id), None)
        if not line:
            return ExplainPlanResponse(
                explanation="No forecast data found for this outlet/SKU/date.",
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )
        rationale = line.rationale_json or {}
        trend_sum = rationale.get("reason_tags", [])
        prompt = FORECAST_EXPLANATION_PROMPT.format(
            outlet_name=outlet.name, sku_name=sku.name,
            date=str(body.plan_date),
            weekday=rationale.get("target_weekday", ""),
            morning=round(line.morning, 1), midday=round(line.midday, 1),
            evening=round(line.evening, 1), total=round(line.total, 1),
            method=line.method, reason_tags=", ".join(trend_sum),
            trend_summary=trend_sum,
        )
        fallback = (
            f"Forecast for {sku.name} at {outlet.name} on {body.plan_date}: "
            f"total {round(line.total, 0)} units (morning {round(line.morning, 0)}, "
            f"midday {round(line.midday, 0)}, evening {round(line.evening, 0)}). "
            f"Based on weighted blend of recent sales and weekday pattern."
        )

    elif ctx == "prep":
        prep_plan = (
            db.query(PrepPlan)
            .filter(PrepPlan.plan_date == body.plan_date)
            .order_by(PrepPlan.created_at.desc())
            .first()
        )
        lines = [l for l in (prep_plan.lines if prep_plan else [])
                 if l.outlet_id == body.outlet_id and l.sku_id == body.sku_id]
        if not lines:
            return ExplainPlanResponse(
                explanation="No prep plan data found.", context_type=ctx,
                outlet_name=outlet.name, sku_name=sku.name,
            )
        rationale = lines[0].rationale_json or {}
        total_prep = sum(l.recommended_units for l in lines)
        prompt = PREP_RATIONALE_PROMPT.format(
            sku_name=sku.name, outlet_name=outlet.name,
            forecast_total=sum((rationale.get("forecast_used") or {}).get(dp, 0) for dp in ("morning", "midday", "evening")),
            current_stock=rationale.get("current_stock", 0),
            safety_buffer_pct=round(rationale.get("safety_buffer_pct", 0.10) * 100, 0),
            waste_rate_pct=round(rationale.get("waste_rate_7d", 0) * 100, 1),
            morning=lines[0].recommended_units if len(lines) > 0 else 0,
            midday=lines[1].recommended_units if len(lines) > 1 else 0,
            evening=lines[2].recommended_units if len(lines) > 2 else 0,
        )
        fallback = (
            f"Total prep recommendation for {sku.name} at {outlet.name}: "
            f"{total_prep} units across all dayparts."
        )

    else:
        fallback = "Explanation not available for this context type."
        prompt = f"Briefly explain the {ctx} data for {sku.name} at {outlet.name} on {body.plan_date}."

    explanation = _call_llm(prompt, fallback)
    return ExplainPlanResponse(
        explanation=explanation, context_type=ctx,
        outlet_name=outlet.name, sku_name=sku.name,
    )


@router.post("/copilot/daily-brief", response_model=DailyBriefResponse)
def generate_daily_brief(body: DailyBriefRequest, db: Session = Depends(get_db)):
    from alerts.waste import detect_waste_risk
    from alerts.stockout import detect_stockout_risk
    from db.models import ForecastRun, ReplenishmentPlan

    brief_date = body.brief_date

    fc_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_date == brief_date)
        .order_by(ForecastRun.created_at.desc())
        .first()
    )
    total_sales = round(sum(l.total for l in (fc_run.lines if fc_run else [])), 0)

    waste_alerts    = detect_waste_risk(brief_date, db)
    stockout_alerts = detect_stockout_risk(brief_date, db)

    repl_plan = (
        db.query(ReplenishmentPlan)
        .filter(ReplenishmentPlan.plan_date == brief_date)
        .order_by(ReplenishmentPlan.created_at.desc())
        .first()
    )
    critical_count = sum(1 for l in (repl_plan.lines if repl_plan else []) if l.urgency == "critical")

    day_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday = day_labels[brief_date.weekday()]

    high_waste = [a for a in waste_alerts if a.risk_level == "high"]
    high_stock = [a for a in stockout_alerts if a.risk_level == "high"]

    at_risk = list({a.outlet_name for a in high_waste + high_stock})
    top_actions_list = []
    for a in high_waste[:2]:
        top_actions_list.append(f"Reduce {a.sku_name} at {a.outlet_name}")
    for a in high_stock[:2]:
        top_actions_list.append(f"Stock up {a.sku_name} at {a.outlet_name}")
    if critical_count > 0:
        top_actions_list.append(f"Place {critical_count} critical ingredient reorder(s)")

    prompt = DAILY_BRIEF_PROMPT.format(
        date=str(brief_date), weekday=weekday,
        total_predicted_sales=total_sales,
        waste_risk_score=min(100, len(waste_alerts) * 10),
        stockout_risk_score=min(100, len(stockout_alerts) * 10),
        high_waste_count=len(high_waste),
        high_stockout_count=len(high_stock),
        critical_reorder_count=critical_count,
        top_actions="; ".join(top_actions_list) or "None",
        at_risk_outlets=", ".join(at_risk) or "None",
    )

    fallback = (
        f"Daily brief for {brief_date} ({weekday}).\n\n"
        f"Total predicted sales: {total_sales} units across all outlets. "
        f"{'High waste risks detected at: ' + ', '.join(at_risk) + '.' if at_risk else 'No critical risks.'}\n\n"
        f"{'Waste alerts: ' + str(len(waste_alerts)) + ' | Stockout alerts: ' + str(len(stockout_alerts)) + '.'}\n\n"
        f"Top actions: {'; '.join(top_actions_list) or 'Review all prep plans before 6am.'}."
    )

    brief = _call_llm(prompt, fallback)
    return DailyBriefResponse(brief=brief, date=str(brief_date))


@router.post("/copilot/run-scenario", response_model=ScenarioResponse)
def run_scenario(body: ScenarioRequest, db: Session = Depends(get_db)):
    target_date = body.target_date or date_type.today()
    result = run_scenario_simulation(body.scenario_text, target_date, db)
    d = result.to_dict()
    return ScenarioResponse(
        scenario=d["scenario"],
        baseline=d["baseline"],
        modified=d["modified"],
        delta=d["delta"],
        recommendation=d["recommendation"],
        interpretation=d["interpretation"],
    )
