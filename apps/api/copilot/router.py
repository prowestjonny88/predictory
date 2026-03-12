"""
Copilot router - Task 18 + Task 21
POST /copilot/explain-plan
POST /copilot/daily-brief
POST /copilot/run-scenario
"""
import os
from datetime import date as date_type
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from alerts.stockout import detect_stockout_risk
from alerts.waste import detect_waste_risk
from copilot.prompts import (
    DAILY_BRIEF_PROMPT,
    FORECAST_EXPLANATION_PROMPT,
    PREP_RATIONALE_PROMPT,
    REPLENISHMENT_RATIONALE_PROMPT,
    STOCKOUT_ALERT_EXPLANATION_PROMPT,
    WASTE_ALERT_EXPLANATION_PROMPT,
)
from copilot.scenario import run_scenario_simulation
from db.database import get_db
from db.models import ForecastRun, Outlet, PrepPlan, ReplenishmentPlan, SKU

router = APIRouter()

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini/gemini-2.5-flash"
DEFAULT_VERTEX_GEMINI_MODEL = "vertex_ai/gemini-1.5-pro"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com"


def _get_env(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _resolve_litellm_config() -> tuple[str, dict]:
    explicit_model = os.getenv("LITELLM_MODEL")
    if explicit_model:
        return explicit_model, {}

    if os.getenv("VERTEXAI_PROJECT") and os.getenv("VERTEXAI_LOCATION"):
        return os.getenv("GEMINI_MODEL", DEFAULT_VERTEX_GEMINI_MODEL), {}

    gemini_api_key = _get_env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if gemini_api_key:
        return (
            os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
            {
                "api_key": gemini_api_key,
                "api_base": os.getenv("GEMINI_API_BASE", GEMINI_API_BASE),
            },
        )

    return DEFAULT_OPENAI_MODEL, {}


def _extract_text(response) -> str:
    content = response.choices[0].message.content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(item["text"])
        content = "\n".join(parts)
    return (content or "").strip()


def _call_llm(prompt: str, fallback: str = "") -> str:
    """
    Call LiteLLM. Returns fallback text if the provider is unavailable.
    All numbers come from deterministic upstream services.
    """
    try:
        import litellm

        model, extra_kwargs = _resolve_litellm_config()
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
            **extra_kwargs,
        )
        text = _extract_text(response)
        return text or fallback
    except Exception as exc:
        return fallback or f"Explanation unavailable: {exc}"


def _score_alerts(alerts: list) -> int:
    score = 0
    for alert in alerts:
        if alert.risk_level == "high":
            score += 20
        elif alert.risk_level == "medium":
            score += 8
    return min(100, score)


def _format_float(value: float) -> str:
    return f"{value:.1f}"


def _get_latest_replenishment_plan(plan_date: date_type, db: Session):
    return (
        db.query(ReplenishmentPlan)
        .filter(ReplenishmentPlan.plan_date == plan_date)
        .order_by(ReplenishmentPlan.created_at.desc())
        .first()
    )


class ExplainPlanRequest(BaseModel):
    outlet_id: int
    sku_id: int
    plan_date: date_type
    context_type: Literal["forecast", "prep", "waste", "stockout", "replenishment"] = "forecast"


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


@router.post("/copilot/explain-plan", response_model=ExplainPlanResponse)
def explain_plan(body: ExplainPlanRequest, db: Session = Depends(get_db)):
    outlet = db.query(Outlet).filter(Outlet.id == body.outlet_id).first()
    sku = db.query(SKU).filter(SKU.id == body.sku_id).first()
    if not outlet or not sku:
        raise HTTPException(status_code=404, detail="Outlet or SKU not found")

    ctx = body.context_type

    if ctx == "forecast":
        fc_run = (
            db.query(ForecastRun)
            .filter(ForecastRun.forecast_date == body.plan_date)
            .order_by(ForecastRun.created_at.desc())
            .first()
        )
        line = next(
            (
                candidate
                for candidate in (fc_run.lines if fc_run else [])
                if candidate.outlet_id == body.outlet_id and candidate.sku_id == body.sku_id
            ),
            None,
        )
        if not line:
            return ExplainPlanResponse(
                explanation="No forecast data found for this outlet/SKU/date.",
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )

        rationale = line.rationale_json or {}
        trend_tags = rationale.get("reason_tags", [])
        prompt = FORECAST_EXPLANATION_PROMPT.format(
            outlet_name=outlet.name,
            sku_name=sku.name,
            date=str(body.plan_date),
            weekday=rationale.get("target_weekday", ""),
            morning=round(line.morning, 1),
            midday=round(line.midday, 1),
            evening=round(line.evening, 1),
            total=round(line.total, 1),
            method=line.method,
            reason_tags=", ".join(trend_tags) or "None",
            trend_summary=", ".join(trend_tags) or "Stable",
        )
        fallback = (
            f"Forecast for {sku.name} at {outlet.name} on {body.plan_date}: total "
            f"{round(line.total, 0)} units (morning {round(line.morning, 0)}, midday "
            f"{round(line.midday, 0)}, evening {round(line.evening, 0)}). Based on a "
            f"weighted blend of recent sales and weekday pattern."
        )

    elif ctx == "prep":
        prep_plan = (
            db.query(PrepPlan)
            .filter(PrepPlan.plan_date == body.plan_date)
            .order_by(PrepPlan.created_at.desc())
            .first()
        )
        lines = [
            line
            for line in (prep_plan.lines if prep_plan else [])
            if line.outlet_id == body.outlet_id and line.sku_id == body.sku_id
        ]
        if not lines:
            return ExplainPlanResponse(
                explanation="No prep plan data found for this outlet/SKU/date.",
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )

        rationale = lines[0].rationale_json or {}
        total_prep = sum(line.recommended_units for line in lines)
        prompt = PREP_RATIONALE_PROMPT.format(
            sku_name=sku.name,
            outlet_name=outlet.name,
            forecast_total=sum(
                (rationale.get("forecast_used") or {}).get(daypart, 0)
                for daypart in ("morning", "midday", "evening")
            ),
            current_stock=rationale.get("current_stock", 0),
            safety_buffer_pct=round(rationale.get("safety_buffer_pct", 0.10) * 100, 0),
            waste_rate_pct=round(rationale.get("waste_rate_7d", 0) * 100, 1),
            morning=lines[0].recommended_units if len(lines) > 0 else 0,
            midday=lines[1].recommended_units if len(lines) > 1 else 0,
            evening=lines[2].recommended_units if len(lines) > 2 else 0,
        )
        fallback = (
            f"Total prep recommendation for {sku.name} at {outlet.name}: {total_prep} "
            f"units across all dayparts."
        )

    elif ctx == "waste":
        alerts = [
            alert
            for alert in detect_waste_risk(body.plan_date, db)
            if alert.outlet_id == body.outlet_id and alert.sku_id == body.sku_id
        ]
        if not alerts:
            return ExplainPlanResponse(
                explanation="No waste alert data found for this outlet/SKU/date.",
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )

        alert = alerts[0]
        prompt = WASTE_ALERT_EXPLANATION_PROMPT.format(
            outlet_name=outlet.name,
            sku_name=sku.name,
            daypart=alert.daypart,
            risk_level=alert.risk_level,
            triggers=", ".join(alert.triggers),
            waste_rate_pct=round(alert.waste_rate * 100, 1),
            excess_prep_units=_format_float(alert.excess_prep_units),
        )
        fallback = (
            f"{sku.name} at {outlet.name} has a {alert.risk_level} waste risk in the "
            f"{alert.daypart}. {alert.reason}."
        )

    elif ctx == "stockout":
        alerts = [
            alert
            for alert in detect_stockout_risk(body.plan_date, db)
            if alert.outlet_id == body.outlet_id and alert.sku_id == body.sku_id
        ]
        if not alerts:
            return ExplainPlanResponse(
                explanation="No stockout alert data found for this outlet/SKU/date.",
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )

        alert = alerts[0]
        prompt = STOCKOUT_ALERT_EXPLANATION_PROMPT.format(
            outlet_name=outlet.name,
            sku_name=sku.name,
            daypart=alert.affected_daypart,
            shortage_qty=_format_float(alert.shortage_qty),
            coverage_pct=_format_float(alert.coverage_pct),
            reason=alert.reason,
        )
        fallback = (
            f"{sku.name} at {outlet.name} has a {alert.risk_level} stockout risk in the "
            f"{alert.affected_daypart}. {alert.reason}."
        )

    else:
        repl_plan = _get_latest_replenishment_plan(body.plan_date, db)
        matching_lines = []
        if repl_plan:
            matching_lines = [
                line
                for line in repl_plan.lines
                if sku.name in (line.driving_skus or [])
            ]

        urgency_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        matching_lines.sort(
            key=lambda line: (
                urgency_rank.get(line.urgency, 4),
                -float(line.reorder_qty),
            )
        )

        if not matching_lines:
            return ExplainPlanResponse(
                explanation="No replenishment recommendation found for this SKU on this date.",
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )

        line = matching_lines[0]
        ingredient = line.ingredient
        unit = ingredient.unit if ingredient else "units"
        prompt = REPLENISHMENT_RATIONALE_PROMPT.format(
            ingredient_name=ingredient.name if ingredient else "Unknown ingredient",
            stock_on_hand=_format_float(line.stock_on_hand),
            unit=unit,
            need_qty=_format_float(line.need_qty),
            reorder_qty=_format_float(line.reorder_qty),
            urgency=line.urgency,
            driving_skus=", ".join(line.driving_skus or []),
            sku_name=sku.name,
        )
        fallback = (
            f"{sku.name} is driving a {line.urgency} reorder recommendation for "
            f"{ingredient.name if ingredient else 'an ingredient'}: need "
            f"{_format_float(line.need_qty)} {unit}, stock {_format_float(line.stock_on_hand)} "
            f"{unit}, reorder {_format_float(line.reorder_qty)} {unit}."
        )

    explanation = _call_llm(prompt, fallback)
    return ExplainPlanResponse(
        explanation=explanation,
        context_type=ctx,
        outlet_name=outlet.name,
        sku_name=sku.name,
    )


@router.post("/copilot/daily-brief", response_model=DailyBriefResponse)
def generate_daily_brief(body: DailyBriefRequest, db: Session = Depends(get_db)):
    brief_date = body.brief_date

    fc_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_date == brief_date)
        .order_by(ForecastRun.created_at.desc())
        .first()
    )
    total_sales = round(sum(line.total for line in (fc_run.lines if fc_run else [])), 0)

    waste_alerts = detect_waste_risk(brief_date, db)
    stockout_alerts = detect_stockout_risk(brief_date, db)
    repl_plan = _get_latest_replenishment_plan(brief_date, db)

    critical_count = sum(
        1 for line in (repl_plan.lines if repl_plan else [])
        if line.urgency == "critical"
    )

    day_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday = day_labels[brief_date.weekday()]

    high_waste = [alert for alert in waste_alerts if alert.risk_level == "high"]
    high_stock = [alert for alert in stockout_alerts if alert.risk_level == "high"]
    waste_risk_score = _score_alerts(waste_alerts)
    stockout_risk_score = _score_alerts(stockout_alerts)

    at_risk = list({alert.outlet_name for alert in high_waste + high_stock})
    top_actions = []
    for alert in high_waste[:2]:
        top_actions.append(f"Reduce {alert.sku_name} at {alert.outlet_name}")
    for alert in high_stock[:2]:
        top_actions.append(f"Stock up {alert.sku_name} at {alert.outlet_name}")
    if critical_count > 0:
        top_actions.append(f"Place {critical_count} critical ingredient reorder(s)")

    prompt = DAILY_BRIEF_PROMPT.format(
        date=str(brief_date),
        weekday=weekday,
        total_predicted_sales=total_sales,
        waste_risk_score=waste_risk_score,
        stockout_risk_score=stockout_risk_score,
        high_waste_count=len(high_waste),
        high_stockout_count=len(high_stock),
        critical_reorder_count=critical_count,
        top_actions="; ".join(top_actions[:3]) or "None",
        at_risk_outlets=", ".join(at_risk) or "None",
    )

    fallback = (
        f"Daily brief for {brief_date} ({weekday}). Total predicted sales are {total_sales} "
        f"units, with waste risk at {waste_risk_score}/100 and stockout risk at "
        f"{stockout_risk_score}/100.\n\n"
        f"Key risks: {len(high_waste)} high waste alerts, {len(high_stock)} high stockout alerts, "
        f"and {critical_count} critical ingredient reorders. "
        f"{'At-risk outlets: ' + ', '.join(at_risk) + '.' if at_risk else 'No outlets are currently flagged as high risk.'}\n\n"
        f"Top actions: {'; '.join(top_actions[:3]) or 'Review the latest prep and replenishment plans before service.'}"
    )

    brief = _call_llm(prompt, fallback)
    return DailyBriefResponse(brief=brief, date=str(brief_date))


@router.post("/copilot/run-scenario", response_model=ScenarioResponse)
def run_scenario(body: ScenarioRequest, db: Session = Depends(get_db)):
    target_date = body.target_date or date_type.today()
    payload = run_scenario_simulation(body.scenario_text, target_date, db).to_dict()
    return ScenarioResponse(
        scenario=payload["scenario"],
        baseline=payload["baseline"],
        modified=payload["modified"],
        delta=payload["delta"],
        recommendation=payload["recommendation"],
        interpretation=payload["interpretation"],
    )
