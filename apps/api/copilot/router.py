"""
Copilot router - Task 18 + Task 21
POST /copilot/explain-plan
POST /copilot/daily-brief
POST /copilot/run-scenario
POST /copilot/daily-actions
"""
import os
from datetime import date as date_type
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from alerts.stockout import detect_stockout_risk
from alerts.waste import detect_waste_risk
from copilot.daily_agent import generate_daily_actions
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
SupportedLanguage = Literal["en", "ms", "zh-CN"]
WEEKDAY_LABELS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "ms": ["Isnin", "Selasa", "Rabu", "Khamis", "Jumaat", "Sabtu", "Ahad"],
    "zh-CN": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"],
}


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


def _normalize_language(language: str | None) -> SupportedLanguage:
    if language in {"en", "ms", "zh-CN"}:
        return language
    return "en"


def _language_prompt_prefix(language: SupportedLanguage) -> str:
    if language == "ms":
        return (
            "Respond in clear operational Bahasa Melayu. Keep all numbers, outlet names, SKU names, "
            "and ingredient names exactly as provided."
        )
    if language == "zh-CN":
        return (
            "Respond in clear operational Simplified Chinese. Keep all numbers, outlet names, SKU "
            "names, and ingredient names exactly as provided."
        )
    return (
        "Respond in clear operational English. Keep all numbers, outlet names, SKU names, and "
        "ingredient names exactly as provided."
    )


def _weekday_label(value: date_type, language: SupportedLanguage) -> str:
    return WEEKDAY_LABELS[language][value.weekday()]


def _localize_fallback_text(key: str, language: SupportedLanguage, **kwargs) -> str:
    if language == "ms":
        templates = {
            "missing_forecast": "Tiada data ramalan untuk cawangan/SKU/tarikh ini.",
            "missing_prep": "Tiada data pelan persediaan untuk cawangan/SKU/tarikh ini.",
            "missing_waste": "Tiada data amaran pembaziran untuk cawangan/SKU/tarikh ini.",
            "missing_stockout": "Tiada data amaran kehabisan stok untuk cawangan/SKU/tarikh ini.",
            "missing_replenishment": "Tiada cadangan pengisian semula untuk SKU ini pada tarikh ini.",
            "forecast": (
                "Ramalan untuk {sku_name} di {outlet_name} pada {plan_date}: jumlah {total} unit "
                "(pagi {morning}, tengah hari {midday}, petang {evening}). Berdasarkan gabungan "
                "jualan terkini dan corak hari yang sama{holiday}{weather}{override}{stockout}."
            ),
            "prep": "Jumlah cadangan persediaan untuk {sku_name} di {outlet_name}: {total_prep} unit merentas semua sesi.",
            "waste": "{sku_name} di {outlet_name} mempunyai risiko pembaziran {risk_level} pada sesi {daypart}. {reason}.",
            "stockout": "{sku_name} di {outlet_name} mempunyai risiko kehabisan stok {risk_level} pada sesi {daypart}. {reason}.",
            "replenishment": (
                "{sku_name} mendorong cadangan pesanan semula {urgency} untuk "
                "{ingredient_name}: perlu {need_qty} {unit}, stok {stock_on_hand} {unit}, "
                "pesan semula {reorder_qty} {unit}."
            ),
            "daily_brief": (
                "Ringkasan harian untuk {brief_date} ({weekday}). Jumlah jualan diramal ialah "
                "{total_sales} unit, dengan risiko pembaziran {waste_risk_score}/100 dan risiko "
                "kehabisan stok {stockout_risk_score}/100.\n\nRisiko utama: {high_waste_count} "
                "amaran pembaziran tinggi, {high_stock_count} amaran kehabisan stok tinggi, dan "
                "{critical_count} pesanan semula bahan kritikal. {at_risk_sentence}\n\nTindakan "
                "utama: {top_actions}"
            ),
        }
    elif language == "zh-CN":
        templates = {
            "missing_forecast": "该门店、SKU 和日期没有预测数据。",
            "missing_prep": "该门店、SKU 和日期没有备货计划数据。",
            "missing_waste": "该门店、SKU 和日期没有浪费预警数据。",
            "missing_stockout": "该门店、SKU 和日期没有缺货预警数据。",
            "missing_replenishment": "该 SKU 在该日期没有补货建议。",
            "forecast": (
                "{plan_date} {outlet_name} 的 {sku_name} 预测总量为 {total} 单位（早上 {morning}，"
                "中午 {midday}，傍晚 {evening}）。该预测基于近期销量与同星期模式的加权组合"
                "{holiday}{weather}{override}{stockout}。"
            ),
            "prep": "{outlet_name} 的 {sku_name} 总备货建议为 {total_prep} 单位，覆盖所有时段。",
            "waste": "{outlet_name} 的 {sku_name} 在 {daypart} 存在 {risk_level} 浪费风险。{reason}。",
            "stockout": "{outlet_name} 的 {sku_name} 在 {daypart} 存在 {risk_level} 缺货风险。{reason}。",
            "replenishment": (
                "{sku_name} 正在推动 {ingredient_name} 的 {urgency} 补货建议：需求 {need_qty} {unit}，"
                "现有库存 {stock_on_hand} {unit}，建议补货 {reorder_qty} {unit}。"
            ),
            "daily_brief": (
                "{brief_date}（{weekday}）每日简报。预测总销量为 {total_sales} 单位，浪费风险为 "
                "{waste_risk_score}/100，缺货风险为 {stockout_risk_score}/100。\n\n主要风险："
                "{high_waste_count} 条高浪费预警，{high_stock_count} 条高缺货预警，以及 "
                "{critical_count} 个关键原料补货事项。{at_risk_sentence}\n\n重点行动：{top_actions}"
            ),
        }
    else:
        templates = {
            "missing_forecast": "No forecast data found for this outlet/SKU/date.",
            "missing_prep": "No prep plan data found for this outlet/SKU/date.",
            "missing_waste": "No waste alert data found for this outlet/SKU/date.",
            "missing_stockout": "No stockout alert data found for this outlet/SKU/date.",
            "missing_replenishment": "No replenishment recommendation found for this SKU on this date.",
            "forecast": (
                "Forecast for {sku_name} at {outlet_name} on {plan_date}: total {total} units "
                "(morning {morning}, midday {midday}, evening {evening}). Based on a weighted "
                "blend of recent sales and weekday pattern{holiday}{weather}{override}{stockout}."
            ),
            "prep": "Total prep recommendation for {sku_name} at {outlet_name}: {total_prep} units across all dayparts.",
            "waste": "{sku_name} at {outlet_name} has a {risk_level} waste risk in the {daypart}. {reason}.",
            "stockout": "{sku_name} at {outlet_name} has a {risk_level} stockout risk in the {daypart}. {reason}.",
            "replenishment": (
                "{sku_name} is driving a {urgency} reorder recommendation for {ingredient_name}: "
                "need {need_qty} {unit}, stock {stock_on_hand} {unit}, reorder {reorder_qty} {unit}."
            ),
            "daily_brief": (
                "Daily brief for {brief_date} ({weekday}). Total predicted sales are {total_sales} "
                "units, with waste risk at {waste_risk_score}/100 and stockout risk at "
                "{stockout_risk_score}/100.\n\nKey risks: {high_waste_count} high waste alerts, "
                "{high_stock_count} high stockout alerts, and {critical_count} critical ingredient "
                "reorders. {at_risk_sentence}\n\nTop actions: {top_actions}"
            ),
        }

    return templates[key].format(**kwargs)


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
    language: str = "en"


class ExplainPlanResponse(BaseModel):
    explanation: str
    context_type: str
    outlet_name: str
    sku_name: str


class DailyBriefRequest(BaseModel):
    brief_date: date_type
    language: str = "en"


class DailyBriefResponse(BaseModel):
    brief: str
    date: str


class ScenarioRequest(BaseModel):
    scenario_text: str
    target_date: Optional[date_type] = None
    language: str = "en"


class ScenarioResponse(BaseModel):
    scenario: str
    baseline: dict
    modified: dict
    delta: dict
    recommendation: str
    interpretation: str


class DailyActionsRequest(BaseModel):
    target_date: date_type
    top_n: int = 5
    language: str = "en"


class ActionTarget(BaseModel):
    outlet_id: Optional[int] = None
    outlet_name: Optional[str] = None
    sku_id: Optional[int] = None
    sku_name: Optional[str] = None
    ingredient_id: Optional[int] = None
    ingredient_name: Optional[str] = None


class AgentAction(BaseModel):
    action_type: Literal["prep", "reorder", "risk", "rebalance"]
    action_text: str
    urgency: Literal["critical", "high", "medium", "low"]
    estimated_impact: str
    target: ActionTarget
    evidence: list[str] = Field(default_factory=list)
    source_type: Literal["deterministic", "llm_rephrased"]


class DailyActionsResponse(BaseModel):
    date: str
    brief: str
    fallback_mode: bool
    top_actions: list[AgentAction] = Field(default_factory=list)
    prep_actions: list[AgentAction] = Field(default_factory=list)
    reorder_actions: list[AgentAction] = Field(default_factory=list)
    risk_warnings: list[AgentAction] = Field(default_factory=list)
    rebalance_suggestions: list[AgentAction] = Field(default_factory=list)


@router.post("/copilot/explain-plan", response_model=ExplainPlanResponse)
def explain_plan(body: ExplainPlanRequest, db: Session = Depends(get_db)):
    language = _normalize_language(body.language)
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
                explanation=_localize_fallback_text("missing_forecast", language),
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )

        rationale = line.rationale_json or {}
        trend_tags = rationale.get("reason_tags", [])
        holiday_signal = rationale.get("holiday_signal") or {}
        weather_signal = rationale.get("weather_signal") or {}
        manual_overrides = rationale.get("manual_overrides") or []
        stockout_censoring = rationale.get("stockout_censoring") or {}
        prompt = f"{_language_prompt_prefix(language)}\n\n" + FORECAST_EXPLANATION_PROMPT.format(
            outlet_name=outlet.name,
            sku_name=sku.name,
            date=str(body.plan_date),
            weekday=rationale.get("target_weekday", ""),
            morning=round(line.morning, 1),
            midday=round(line.midday, 1),
            evening=round(line.evening, 1),
            total=round(line.total, 1),
            method=line.method,
            baseline_total=round(rationale.get("baseline_total", line.total), 1),
            context_adjustment_pct=round(rationale.get("context_adjustment_pct", 0.0), 1),
            holiday_context=holiday_signal.get("label", "None"),
            weather_context=(
                f"{weather_signal.get('label', 'None')} "
                f"({weather_signal.get('adjustment_pct', 0.0):.1f}%)"
            ),
            manual_override_summary=(
                ", ".join(
                    f"{override.get('title', 'Override')} ({override.get('adjustment_pct', 0.0):.1f}%)"
                    for override in manual_overrides
                )
                or "None"
            ),
            stockout_recovery_summary=(
                f"{stockout_censoring.get('adjusted_history_days', 0)} day(s) adjusted"
                if stockout_censoring.get("adjusted_history_days", 0) > 0
                else stockout_censoring.get("note", "None")
            ),
            reason_tags=", ".join(trend_tags) or "None",
            trend_summary=", ".join(trend_tags) or "Stable",
        )
        fallback = _localize_fallback_text(
            "forecast",
            language,
            sku_name=sku.name,
            outlet_name=outlet.name,
            plan_date=body.plan_date,
            total=round(line.total, 0),
            morning=round(line.morning, 0),
            midday=round(line.midday, 0),
            evening=round(line.evening, 0),
            holiday=(
                "; penanda cuti aktif"
                if language == "ms" and holiday_signal
                else "；已应用假期标记"
                if language == "zh-CN" and holiday_signal
                else "; holiday flag active"
                if holiday_signal
                else ""
            ),
            weather=(
                "; pelarasan cuaca digunakan"
                if language == "ms" and weather_signal.get("adjustment_pct", 0.0)
                else "；已应用天气调整"
                if language == "zh-CN" and weather_signal.get("adjustment_pct", 0.0)
                else "; weather adjustment applied"
                if weather_signal.get("adjustment_pct", 0.0)
                else ""
            ),
            override=(
                "; override manual digunakan"
                if language == "ms" and manual_overrides
                else "；已应用手动覆盖"
                if language == "zh-CN" and manual_overrides
                else "; manual override applied"
                if manual_overrides
                else ""
            ),
            stockout=(
                "; sejarah dilaras oleh pemulihan kehabisan stok"
                if language == "ms" and stockout_censoring.get("adjusted_history_days", 0)
                else "；历史已按缺货情况修正"
                if language == "zh-CN" and stockout_censoring.get("adjusted_history_days", 0)
                else "; stockout recovery adjusted history"
                if stockout_censoring.get("adjusted_history_days", 0)
                else ""
            ),
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
                explanation=_localize_fallback_text("missing_prep", language),
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )

        rationale = lines[0].rationale_json or {}
        total_prep = sum(line.recommended_units for line in lines)
        prompt = f"{_language_prompt_prefix(language)}\n\n" + PREP_RATIONALE_PROMPT.format(
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
        fallback = _localize_fallback_text(
            "prep",
            language,
            sku_name=sku.name,
            outlet_name=outlet.name,
            total_prep=total_prep,
        )

    elif ctx == "waste":
        alerts = [
            alert
            for alert in detect_waste_risk(body.plan_date, db)
            if alert.outlet_id == body.outlet_id and alert.sku_id == body.sku_id
        ]
        if not alerts:
            return ExplainPlanResponse(
                explanation=_localize_fallback_text("missing_waste", language),
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )

        alert = alerts[0]
        prompt = f"{_language_prompt_prefix(language)}\n\n" + WASTE_ALERT_EXPLANATION_PROMPT.format(
            outlet_name=outlet.name,
            sku_name=sku.name,
            daypart=alert.daypart,
            risk_level=alert.risk_level,
            triggers=", ".join(alert.triggers),
            waste_rate_pct=round(alert.waste_rate * 100, 1),
            excess_prep_units=_format_float(alert.excess_prep_units),
        )
        fallback = _localize_fallback_text(
            "waste",
            language,
            sku_name=sku.name,
            outlet_name=outlet.name,
            risk_level=alert.risk_level,
            daypart=alert.daypart,
            reason=alert.reason,
        )

    elif ctx == "stockout":
        alerts = [
            alert
            for alert in detect_stockout_risk(body.plan_date, db)
            if alert.outlet_id == body.outlet_id and alert.sku_id == body.sku_id
        ]
        if not alerts:
            return ExplainPlanResponse(
                explanation=_localize_fallback_text("missing_stockout", language),
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )

        alert = alerts[0]
        prompt = f"{_language_prompt_prefix(language)}\n\n" + STOCKOUT_ALERT_EXPLANATION_PROMPT.format(
            outlet_name=outlet.name,
            sku_name=sku.name,
            daypart=alert.affected_daypart,
            shortage_qty=_format_float(alert.shortage_qty),
            coverage_pct=_format_float(alert.coverage_pct),
            reason=alert.reason,
        )
        fallback = _localize_fallback_text(
            "stockout",
            language,
            sku_name=sku.name,
            outlet_name=outlet.name,
            risk_level=alert.risk_level,
            daypart=alert.affected_daypart,
            reason=alert.reason,
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
                explanation=_localize_fallback_text("missing_replenishment", language),
                context_type=ctx,
                outlet_name=outlet.name,
                sku_name=sku.name,
            )

        line = matching_lines[0]
        ingredient = line.ingredient
        unit = ingredient.unit if ingredient else "units"
        prompt = f"{_language_prompt_prefix(language)}\n\n" + REPLENISHMENT_RATIONALE_PROMPT.format(
            ingredient_name=ingredient.name if ingredient else "Unknown ingredient",
            stock_on_hand=_format_float(line.stock_on_hand),
            unit=unit,
            need_qty=_format_float(line.need_qty),
            reorder_qty=_format_float(line.reorder_qty),
            urgency=line.urgency,
            driving_skus=", ".join(line.driving_skus or []),
            sku_name=sku.name,
        )
        fallback = _localize_fallback_text(
            "replenishment",
            language,
            sku_name=sku.name,
            urgency=line.urgency,
            ingredient_name=ingredient.name if ingredient else "ingredient",
            need_qty=_format_float(line.need_qty),
            stock_on_hand=_format_float(line.stock_on_hand),
            reorder_qty=_format_float(line.reorder_qty),
            unit=unit,
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
    language = _normalize_language(body.language)

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

    weekday = _weekday_label(brief_date, language)

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

    prompt = f"{_language_prompt_prefix(language)}\n\n" + DAILY_BRIEF_PROMPT.format(
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

    at_risk_sentence = (
        (
            ("Cawangan berisiko: " if language == "ms" else "高风险门店：" if language == "zh-CN" else "At-risk outlets: ")
            + ", ".join(at_risk)
            + "."
        )
        if at_risk
        else (
            "Tiada cawangan berisiko tinggi pada masa ini."
            if language == "ms"
            else "目前没有被标记为高风险的门店。"
            if language == "zh-CN"
            else "No outlets are currently flagged as high risk."
        )
    )
    fallback = _localize_fallback_text(
        "daily_brief",
        language,
        brief_date=brief_date,
        weekday=weekday,
        total_sales=total_sales,
        waste_risk_score=waste_risk_score,
        stockout_risk_score=stockout_risk_score,
        high_waste_count=len(high_waste),
        high_stock_count=len(high_stock),
        critical_count=critical_count,
        at_risk_sentence=at_risk_sentence,
        top_actions="; ".join(top_actions[:3])
        or (
            "Semak pelan persediaan dan pengisian semula terkini sebelum operasi."
            if language == "ms"
            else "在营业前复核最新备货和补货计划。"
            if language == "zh-CN"
            else "Review the latest prep and replenishment plans before service."
        ),
    )

    brief = _call_llm(prompt, fallback)
    return DailyBriefResponse(brief=brief, date=str(brief_date))


@router.post("/copilot/run-scenario", response_model=ScenarioResponse)
def run_scenario(body: ScenarioRequest, db: Session = Depends(get_db)):
    target_date = body.target_date or date_type.today()
    language = _normalize_language(body.language)
    payload = run_scenario_simulation(body.scenario_text, target_date, db, language).to_dict()
    return ScenarioResponse(
        scenario=payload["scenario"],
        baseline=payload["baseline"],
        modified=payload["modified"],
        delta=payload["delta"],
        recommendation=payload["recommendation"],
        interpretation=payload["interpretation"],
    )


@router.post("/copilot/daily-actions", response_model=DailyActionsResponse)
def daily_actions(body: DailyActionsRequest, db: Session = Depends(get_db)):
    language = _normalize_language(body.language)
    llm = lambda prompt, fallback="": _call_llm(
        f"{_language_prompt_prefix(language)}\n\n{prompt}",
        fallback,
    )
    payload = generate_daily_actions(body.target_date, body.top_n, db, llm, language)
    return DailyActionsResponse(
        date=payload["date"],
        brief=payload["brief"],
        fallback_mode=payload["fallback_mode"],
        top_actions=payload["top_actions"],
        prep_actions=payload["prep_actions"],
        reorder_actions=payload["reorder_actions"],
        risk_warnings=payload["risk_warnings"],
        rebalance_suggestions=payload["rebalance_suggestions"],
    )
