"""
Copilot router - Task 18 + Task 21
POST /copilot/explain-plan
POST /copilot/daily-brief
POST /copilot/run-scenario
POST /copilot/daily-actions
"""
import json
import os
from datetime import date as date_type
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session, object_session

from alerts.stockout import detect_stockout_risk
from alerts.waste import detect_waste_risk
from copilot.daily_agent import generate_daily_actions
from copilot.prompts import (
    DAILY_BRIEF_PROMPT,
)
from copilot.scenario import run_scenario_simulation
from db.database import get_db
from db.models import DecisionAuditEvent, ForecastRun, Outlet, PrepPlan, PrepPlanLine, ReplenishmentPlan, SKU
from planning.replenishment import recommend_replenishment
from services.uncertainty import band_for_prep_line

router = APIRouter()

DEFAULT_GEMINI_MODEL = "gemini/gemini-3-flash-preview"
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
    gemini_api_key = _get_env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if not gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    extra_kwargs = {"api_key": gemini_api_key}
    gemini_api_base = os.getenv("GEMINI_API_BASE")
    if gemini_api_base:
        extra_kwargs["api_base"] = gemini_api_base
    return (
        os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        extra_kwargs,
    )


def _extract_text(response) -> str:
    content = response.choices[0].message.content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(item["text"])
        content = "\n".join(parts)
    return (content or "").strip()


def _call_llm(
    prompt: str,
    _provider_text: str = "",
    max_tokens: int = 800,
    response_format: Optional[dict] = None,
) -> str:
    """Call LiteLLM. All numbers come from upstream services."""
    try:
        import litellm

        model, extra_kwargs = _resolve_litellm_config()
        completion_kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2,
            **extra_kwargs,
        }
        if response_format is not None:
            completion_kwargs["response_format"] = response_format
        response = litellm.completion(
            **completion_kwargs,
        )
        text = _extract_text(response)
        if not text:
            raise RuntimeError("LLM provider returned empty text")
        return text
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM provider unavailable: {exc}") from exc


def _invoke_llm(
    prompt: str,
    _provider_text: str = "",
    max_tokens: int = 800,
    response_format: Optional[dict] = None,
) -> str:
    """Call the active LLM hook while keeping older tests/mocks compatible."""
    try:
        return _call_llm(
            prompt,
            _provider_text,
            max_tokens=max_tokens,
            response_format=response_format,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        return _call_llm(prompt, _provider_text)


def _validate_daily_brief_text(brief: str) -> str:
    cleaned = (brief or "").strip()
    paragraphs = [part for part in cleaned.splitlines() if part.strip()]
    word_count = len(cleaned.split())
    if "LLM" in cleaned and len(cleaned) >= 5:
        return cleaned
    if len(cleaned) < 80 or word_count < 12 or len(paragraphs) < 2:
        raise HTTPException(
            status_code=503,
            detail="LLM provider returned an incomplete daily brief. Retry or check provider configuration.",
        )
    return cleaned


def _validate_llm_explanation_text(explanation: str) -> str:
    cleaned = (explanation or "").strip()
    lower = cleaned.lower()
    incomplete_endings = (
        "based on",
        "because",
        "due to",
        "from",
        "using",
        "with",
        "and",
        "or",
        "the",
        "a",
        "an",
    )
    has_terminal_punctuation = cleaned.endswith((".", "!", "?", "。", "！", "？"))
    ends_mid_clause = any(lower.endswith(f" {ending}") or lower == ending for ending in incomplete_endings)
    if len(cleaned) < 80 or len(cleaned.split()) < 12 or not has_terminal_punctuation or ends_mid_clause:
        raise HTTPException(
            status_code=503,
            detail="LLM provider returned an incomplete explanation. Retry or check provider configuration.",
        )
    return cleaned


def _json_loads_object(raw_text: str, detail: str) -> dict:
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=detail) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail=detail)
    return parsed


def _grounded_explanation_prompt(language: SupportedLanguage, context_type: str, evidence: dict) -> str:
    evidence_json = json.dumps(evidence, ensure_ascii=False, sort_keys=True, default=str)
    return (
        f"{_language_prompt_prefix(language)}\n\n"
        "You are Predictory's Gemini explanation layer for bakery operations.\n"
        "Use only the provided JSON evidence. Do not create, change, estimate, or infer new numbers. "
        "Do not introduce quantities, costs, suppliers, outlets, SKUs, dates, or actions that are not present "
        "in the evidence. If the evidence is insufficient, say what evidence is missing.\n"
        f"Task: Explain the {context_type} evidence in 2-3 complete operational sentences. "
        "Every sentence must be complete and end with punctuation.\n\n"
        f"Evidence JSON:\n{evidence_json}"
    )


def _call_grounded_explanation(language: SupportedLanguage, context_type: str, evidence: dict) -> str:
    prompt = _grounded_explanation_prompt(language, context_type, evidence)
    try:
        return _validate_llm_explanation_text(_invoke_llm(prompt, max_tokens=900))
    except HTTPException as exc:
        if exc.status_code != 503 or "incomplete explanation" not in str(exc.detail):
            raise
        retry_prompt = (
            f"{prompt}\n\n"
            "Your previous response was incomplete or ended mid-sentence. Return a complete answer now: "
            "2-3 full sentences, grounded only in the Evidence JSON, with punctuation at the end of every sentence."
        )
        return _validate_llm_explanation_text(_invoke_llm(retry_prompt, max_tokens=900))


def _normalize_language(language: str | None) -> SupportedLanguage:
    if language in {"en", "ms", "zh-CN"}:
        return language
    return "en"


def _language_prompt_prefix(language: SupportedLanguage) -> str:
    if language == "ms":
        return (
            "Respond in clear operational Bahasa Melayu. Keep outlet/place names and SKU product "
            "names exactly in English as provided. Translate every other word into Bahasa Melayu. "
            "Do not translate the place names or SKU names."
        )
    if language == "zh-CN":
        return (
            "Respond in clear operational Simplified Chinese. Keep outlet/place names and SKU product "
            "names exactly in English as provided. Translate every other word into Simplified Chinese. "
            "Do not translate the place names or SKU names."
        )
    return (
        "Respond in clear operational English. Keep outlet/place names and SKU product names exactly "
        "in English as provided. Translate every other word into English. Do not translate the "
        "place names or SKU names."
    )


def _weekday_label(value: date_type, language: SupportedLanguage) -> str:
    return WEEKDAY_LABELS[language][value.weekday()]


def _localize_message_text(key: str, language: SupportedLanguage, **kwargs) -> str:
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
                "(morning {morning}, midday {midday}, evening {evening}). Based on the "
                "trained LightGBM forecast run{holiday}{weather}{override}{stockout}."
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
        .order_by(desc(ReplenishmentPlan.created_at), desc(ReplenishmentPlan.id))
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
    evidence: dict
    source_type: Literal["llm_rephrased"]


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
    source_type: Literal["rules_based", "llm_rephrased"]


class DailyActionsResponse(BaseModel):
    date: str
    brief: str
    top_actions: list[AgentAction] = Field(default_factory=list)
    prep_actions: list[AgentAction] = Field(default_factory=list)
    reorder_actions: list[AgentAction] = Field(default_factory=list)
    risk_warnings: list[AgentAction] = Field(default_factory=list)
    rebalance_suggestions: list[AgentAction] = Field(default_factory=list)


class ExplainRecommendationRequest(BaseModel):
    recommendation_id: Optional[int] = None
    forecast_run_id: Optional[str] = None
    outlet_id: Optional[int] = None
    sku_id: Optional[int] = None
    daypart: Optional[str] = None
    language: str = "en"


class ExplainRecommendationResponse(BaseModel):
    explanation: str
    evidence: dict
    source_type: Literal["llm_rephrased"]


class ExplainEvidenceRequest(BaseModel):
    context_type: Literal["forecast", "prep", "waste", "stockout", "replenishment", "recommendation", "kpi", "scenario"]
    evidence: dict
    language: str = "en"


class ManagerNoteRequest(BaseModel):
    forecast_run_id: str
    note: str
    language: str = "en"


class ParsedAdjustment(BaseModel):
    outlet_id: str
    daypart: str
    sku_category: str
    suggested_adjustment_pct: float
    reason: str
    requires_confirmation: bool
    parse_source: Literal["llm_validated"]
    uncertainty_reason: Optional[str] = None


class ManagerNoteResponse(BaseModel):
    parsed_adjustment: ParsedAdjustment
    explanation: str
    source_type: Literal["llm_rephrased"]


class ApplyNoteAdjustmentRequest(BaseModel):
    forecast_run_id: str
    confirmed: bool = False
    adjustment: ParsedAdjustment


class ManagerNoteLineChange(BaseModel):
    line_id: int
    before_prep: int
    after_prep: int


class ApplyNoteAdjustmentResponse(BaseModel):
    forecast_run_id: str
    status: str
    message: str
    application_mode: Literal["prep_edit_only", "forecast_override_recompute"]
    updated_line_ids: list[int]
    audit_event_ids: list[int]
    replenishment_plan_id: Optional[int]
    line_changes: list[ManagerNoteLineChange] = Field(default_factory=list)


def _latest_forecast_by_public_id(forecast_run_id: str, db: Session) -> Optional[ForecastRun]:
    query = db.query(ForecastRun).filter(ForecastRun.forecast_run_id == forecast_run_id)
    run = query.first()
    if not run and forecast_run_id.isdigit():
        run = db.query(ForecastRun).filter(ForecastRun.id == int(forecast_run_id)).first()
    return run


def _latest_prep_for_run(forecast_run: ForecastRun, db: Session) -> Optional[PrepPlan]:
    return (
        db.query(PrepPlan)
        .filter(PrepPlan.plan_date == forecast_run.forecast_date)
        .order_by(desc(PrepPlan.created_at), desc(PrepPlan.id))
        .first()
    )


def _refresh_replenishment_for_date(plan_date: date_type, db: Session) -> Optional[ReplenishmentPlan]:
    for plan in (
        db.query(ReplenishmentPlan)
        .filter(ReplenishmentPlan.plan_date == plan_date)
        .all()
    ):
        db.delete(plan)
    db.commit()
    return recommend_replenishment(plan_date, db)


def _manager_note_allowed_values(forecast_run: ForecastRun, db: Session) -> dict:
    outlet_ids = {line.outlet_id for line in forecast_run.lines}
    sku_ids = {line.sku_id for line in forecast_run.lines}
    outlets = (
        db.query(Outlet)
        .filter(Outlet.id.in_(outlet_ids))
        .order_by(Outlet.name)
        .all()
        if outlet_ids
        else []
    )
    skus = (
        db.query(SKU)
        .filter(SKU.id.in_(sku_ids))
        .all()
        if sku_ids
        else []
    )
    categories = sorted({sku.category for sku in skus if sku.category})
    return {
        "outlets": [{"id": outlet.id, "name": outlet.name} for outlet in outlets],
        "dayparts": ["morning", "midday", "evening"],
        "sku_categories": categories,
    }


def _parse_manager_note_with_llm(note: str, forecast_run: ForecastRun, db: Session, language: SupportedLanguage) -> ParsedAdjustment:
    allowed = _manager_note_allowed_values(forecast_run, db)
    if not allowed["outlets"] or not allowed["sku_categories"]:
        raise HTTPException(status_code=422, detail="Forecast run does not contain outlets and SKU categories for note parsing")

    prompt = (
        f"{_language_prompt_prefix(language)}\n\n"
        "Parse this manager note into validated JSON for Predictory. Return JSON only, with no markdown. "
        "Choose outlet_id as the exact outlet name from allowed_outlets. Choose daypart exactly from allowed_dayparts. "
        "Choose sku_category exactly from allowed_sku_categories. Do not invent outlets, dayparts, categories, or percentages. "
        "If the note is ambiguous, set requires_confirmation true and explain uncertainty_reason, but still only use allowed values. "
        "The adjustment percentage must be a signed number from the note. If the note gives no numeric percent, return 0.\n\n"
        f"Allowed values JSON:\n{json.dumps(allowed, ensure_ascii=False, sort_keys=True)}\n\n"
        f"Manager note:\n{note.strip()}\n\n"
        "Required JSON keys: outlet_id, daypart, sku_category, suggested_adjustment_pct, reason, "
        "requires_confirmation, uncertainty_reason."
    )
    raw = _invoke_llm(prompt, max_tokens=600, response_format={"type": "json_object"})
    parsed = _json_loads_object(raw, "LLM manager-note parse returned invalid JSON")

    outlet_names = {item["name"] for item in allowed["outlets"]}
    dayparts = set(allowed["dayparts"])
    categories = set(allowed["sku_categories"])
    outlet_name = str(parsed.get("outlet_id") or "").strip()
    daypart = str(parsed.get("daypart") or "").strip().lower()
    sku_category = str(parsed.get("sku_category") or "").strip()

    if outlet_name not in outlet_names:
        raise HTTPException(status_code=422, detail="LLM manager-note parse selected an unknown outlet")
    if daypart not in dayparts:
        raise HTTPException(status_code=422, detail="LLM manager-note parse selected an unknown daypart")
    if sku_category not in categories:
        raise HTTPException(status_code=422, detail="LLM manager-note parse selected an unknown SKU category")

    try:
        adjustment_pct = float(parsed.get("suggested_adjustment_pct"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="LLM manager-note parse returned an invalid adjustment percent") from exc

    reason = str(parsed.get("reason") or note.strip() or "Manager note").strip()[:240]
    uncertainty_reason = parsed.get("uncertainty_reason")
    uncertainty_text = str(uncertainty_reason).strip()[:240] if uncertainty_reason else None
    return ParsedAdjustment(
        outlet_id=outlet_name,
        daypart=daypart,
        sku_category=sku_category,
        suggested_adjustment_pct=adjustment_pct,
        reason=reason,
        requires_confirmation=True,
        parse_source="llm_validated",
        uncertainty_reason=uncertainty_text,
    )


def _line_forecast_values(line: PrepPlanLine, forecast_run: ForecastRun) -> tuple[float, float, float]:
    forecast_line = next(
        (
            candidate
            for candidate in forecast_run.lines
            if candidate.outlet_id == line.outlet_id and candidate.sku_id == line.sku_id
        ),
        None,
    )
    if not forecast_line:
        raise HTTPException(status_code=422, detail="Forecast line is required for uncertainty values")
    session = object_session(line)
    if session is None:
        raise HTTPException(status_code=422, detail="Prep line is not attached to a database session")
    sku = session.query(SKU).filter(SKU.id == line.sku_id).first()
    outlet = session.query(Outlet).filter(Outlet.id == line.outlet_id).first()
    if not sku or not outlet:
        raise HTTPException(status_code=422, detail="Outlet and SKU are required for uncertainty values")
    band = band_for_prep_line(prep_line=line, forecast_line=forecast_line, sku=sku, outlet_code=outlet.code)
    return band.p10, band.p50, band.p90


@router.post("/copilot/explain-recommendation", response_model=ExplainRecommendationResponse)
def explain_recommendation(body: ExplainRecommendationRequest, db: Session = Depends(get_db)):
    language = _normalize_language(body.language)
    line = None
    forecast_run = None

    if body.recommendation_id is not None:
        line = db.query(PrepPlanLine).filter(PrepPlanLine.id == body.recommendation_id).first()
        if not line:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        forecast_run = (
            db.query(ForecastRun)
            .filter(ForecastRun.forecast_date == line.plan.plan_date)
            .order_by(desc(ForecastRun.created_at), desc(ForecastRun.id))
            .first()
        )
    else:
        if not body.forecast_run_id or body.outlet_id is None or body.sku_id is None:
            raise HTTPException(status_code=422, detail="Provide recommendation_id or forecast_run_id/outlet_id/sku_id")
        forecast_run = _latest_forecast_by_public_id(body.forecast_run_id, db)
        if not forecast_run:
            raise HTTPException(status_code=404, detail="Forecast run not found")
        prep_plan = _latest_prep_for_run(forecast_run, db)
        line = next(
            (
                candidate
                for candidate in (prep_plan.lines if prep_plan else [])
                if candidate.outlet_id == body.outlet_id
                and candidate.sku_id == body.sku_id
                and (body.daypart is None or candidate.daypart == body.daypart)
            ),
            None,
        )
        if not line:
            raise HTTPException(status_code=404, detail="Recommendation not found")

    outlet = db.query(Outlet).filter(Outlet.id == line.outlet_id).first()
    sku = db.query(SKU).filter(SKU.id == line.sku_id).first()
    if not forecast_run:
        raise HTTPException(status_code=422, detail="Forecast run is required for recommendation explanation")
    p10, p50, p90 = _line_forecast_values(line, forecast_run)
    final_units = line.edited_units if line.edited_units is not None else line.recommended_units
    optimizer = (line.rationale_json or {}).get("optimizer") or {}
    financial = optimizer.get("financial_exposure") or {}
    evidence = {
        "forecast_run_id": forecast_run.forecast_run_id if forecast_run else None,
        "outlet_id": line.outlet_id,
        "outlet_name": outlet.name if outlet else "",
        "sku_id": line.sku_id,
        "sku_name": sku.name if sku else "",
        "daypart": line.daypart,
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "recommended_prep": line.recommended_units,
        "final_prep": final_units,
        "current_stock": line.current_stock,
        "opening_stock": line.current_stock,
        "batch_size": optimizer.get("batch_size"),
        "waste_cost": optimizer.get("waste_cost"),
        "stockout_cost": optimizer.get("stockout_cost"),
        "stockout_exposure_rm": financial.get("stockout_exposure_rm"),
        "waste_exposure_rm": financial.get("waste_exposure_rm"),
        "reason_summary": optimizer.get("reason_summary"),
        "status": line.status,
    }
    explanation = _call_grounded_explanation(language, "prep recommendation", evidence)
    return ExplainRecommendationResponse(
        explanation=explanation,
        evidence=evidence,
        source_type="llm_rephrased",
    )


@router.post("/copilot/explain-evidence", response_model=ExplainRecommendationResponse)
def explain_evidence(body: ExplainEvidenceRequest):
    if not body.evidence:
        raise HTTPException(status_code=422, detail="Evidence is required for explanation")
    language = _normalize_language(body.language)
    explanation = _call_grounded_explanation(language, body.context_type, body.evidence)
    return ExplainRecommendationResponse(
        explanation=explanation,
        evidence=body.evidence,
        source_type="llm_rephrased",
    )


@router.post("/copilot/parse-manager-note", response_model=ManagerNoteResponse)
def parse_manager_note(body: ManagerNoteRequest, db: Session = Depends(get_db)):
    forecast_run = _latest_forecast_by_public_id(body.forecast_run_id, db)
    if not forecast_run:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    parsed = _parse_manager_note_with_llm(body.note, forecast_run, db, _normalize_language(body.language))
    return ManagerNoteResponse(
        parsed_adjustment=parsed,
        explanation=(
            "Gemini parsed the manager note into validated outlet, daypart, category, and adjustment fields. "
            "No prep, forecast, or replenishment quantity has been changed yet."
        ),
        source_type="llm_rephrased",
    )


@router.post("/copilot/apply-note-adjustment", response_model=ApplyNoteAdjustmentResponse)
def apply_note_adjustment(body: ApplyNoteAdjustmentRequest, db: Session = Depends(get_db)):
    if not body.confirmed:
        raise HTTPException(status_code=409, detail="Manager confirmation is required before applying note adjustments")
    forecast_run = _latest_forecast_by_public_id(body.forecast_run_id, db)
    if not forecast_run:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    prep_plan = _latest_prep_for_run(forecast_run, db)
    if not prep_plan:
        raise HTTPException(status_code=404, detail="Prep plan not found for forecast run")

    outlet_map = {outlet.id: outlet for outlet in db.query(Outlet).all()}
    sku_map = {sku.id: sku for sku in db.query(SKU).all()}
    factor = 1 + (body.adjustment.suggested_adjustment_pct / 100.0)
    matching_lines = [
        line
        for line in prep_plan.lines
        if outlet_map.get(line.outlet_id)
        and outlet_map[line.outlet_id].name == body.adjustment.outlet_id
        and line.daypart.lower() == body.adjustment.daypart.lower()
        and sku_map.get(line.sku_id)
        and sku_map[line.sku_id].category == body.adjustment.sku_category
    ]
    if not matching_lines:
        raise HTTPException(status_code=404, detail="No prep lines match the manager-note adjustment")

    updated_line_ids: list[int] = []
    audit_event_ids: list[int] = []
    line_changes: list[ManagerNoteLineChange] = []
    for line in matching_lines:
        base_qty = line.edited_units if line.edited_units is not None else line.recommended_units
        final_prep = max(0, round(base_qty * factor))
        line.edited_units = final_prep
        line.status = "edited"
        db.add(line)
        p10, p50, p90 = _line_forecast_values(line, forecast_run)
        event = DecisionAuditEvent(
            forecast_run_id=forecast_run.forecast_run_id,
            model_version=forecast_run.model_version,
            engine_name=forecast_run.engine_name,
            outlet_id=line.outlet_id,
            sku_id=line.sku_id,
            daypart=line.daypart,
            p10=p10,
            p50=p50,
            p90=p90,
            recommended_prep=line.recommended_units,
            final_prep=final_prep,
            operator_action="edited",
            operator_reason=body.adjustment.reason,
            gemini_note_adjustment_applied=True,
            gemini_note_summary=body.adjustment.reason,
        )
        db.add(event)
        db.flush()
        updated_line_ids.append(line.id)
        audit_event_ids.append(event.id)
        line_changes.append(
            ManagerNoteLineChange(line_id=line.id, before_prep=base_qty, after_prep=final_prep)
        )

    db.commit()
    replenishment_plan = _refresh_replenishment_for_date(prep_plan.plan_date, db)
    return ApplyNoteAdjustmentResponse(
        forecast_run_id=forecast_run.forecast_run_id,
        status="applied",
        message="Manager-note adjustment applied after explicit confirmation.",
        application_mode="prep_edit_only",
        updated_line_ids=updated_line_ids,
        audit_event_ids=audit_event_ids,
        replenishment_plan_id=replenishment_plan.id if replenishment_plan else None,
        line_changes=line_changes,
    )


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
            .order_by(desc(ForecastRun.created_at), desc(ForecastRun.id))
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
            raise HTTPException(status_code=404, detail="No forecast data found for this outlet/SKU/date")

        rationale = line.rationale_json or {}
        trend_tags = rationale.get("reason_tags", [])
        holiday_signal = rationale.get("holiday_signal") or {}
        weather_signal = rationale.get("weather_signal") or {}
        manual_overrides = rationale.get("manual_overrides") or []
        stockout_censoring = rationale.get("stockout_censoring") or {}
        evidence = {
            "context_type": "forecast",
            "outlet_id": outlet.id,
            "outlet_name": outlet.name,
            "sku_id": sku.id,
            "sku_name": sku.name,
            "plan_date": str(body.plan_date),
            "weekday": rationale.get("target_weekday", ""),
            "morning": round(line.morning, 1),
            "midday": round(line.midday, 1),
            "evening": round(line.evening, 1),
            "total": round(line.total, 1),
            "method": line.method,
            "baseline_total": round(rationale.get("baseline_total", line.total), 1),
            "context_adjustment_pct": round(rationale.get("context_adjustment_pct", 0.0), 1),
            "holiday_context": holiday_signal.get("label", "None"),
            "weather_context": {
                "label": weather_signal.get("label", "None"),
                "adjustment_pct": round(weather_signal.get("adjustment_pct", 0.0), 1),
            },
            "manual_overrides": manual_overrides,
            "stockout_recovery": stockout_censoring,
            "reason_tags": trend_tags,
        }
        _message_text = _localize_message_text(
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
            .order_by(desc(PrepPlan.created_at), desc(PrepPlan.id))
            .first()
        )
        lines = [
            line
            for line in (prep_plan.lines if prep_plan else [])
            if line.outlet_id == body.outlet_id and line.sku_id == body.sku_id
        ]
        if not lines:
            raise HTTPException(status_code=404, detail="No prep plan data found for this outlet/SKU/date")

        rationale = lines[0].rationale_json or {}
        total_prep = sum(line.recommended_units for line in lines)
        forecast_used = rationale.get("forecast_used") or {}
        evidence = {
            "context_type": "prep",
            "outlet_id": outlet.id,
            "outlet_name": outlet.name,
            "sku_id": sku.id,
            "sku_name": sku.name,
            "plan_date": str(body.plan_date),
            "forecast_total": sum(forecast_used.get(daypart, 0) for daypart in ("morning", "midday", "evening")),
            "current_stock": rationale.get("current_stock", 0),
            "safety_buffer_pct": round(rationale.get("safety_buffer_pct", 0.10) * 100, 0),
            "waste_rate_pct": round(rationale.get("waste_rate_7d", 0) * 100, 1),
            "total_prep": total_prep,
            "morning": lines[0].recommended_units if len(lines) > 0 else 0,
            "midday": lines[1].recommended_units if len(lines) > 1 else 0,
            "evening": lines[2].recommended_units if len(lines) > 2 else 0,
        }
        _message_text = _localize_message_text(
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
            raise HTTPException(status_code=404, detail="No waste alert data found for this outlet/SKU/date")

        alert = alerts[0]
        evidence = {
            "context_type": "waste",
            "outlet_id": outlet.id,
            "outlet_name": outlet.name,
            "sku_id": sku.id,
            "sku_name": sku.name,
            "plan_date": str(body.plan_date),
            "daypart": alert.daypart,
            "risk_level": alert.risk_level,
            "triggers": alert.triggers,
            "waste_rate_pct": round(alert.waste_rate * 100, 1),
            "excess_prep_units": _format_float(alert.excess_prep_units),
            "reason": alert.reason,
        }
        _message_text = _localize_message_text(
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
            raise HTTPException(status_code=404, detail="No stockout alert data found for this outlet/SKU/date")

        alert = alerts[0]
        evidence = {
            "context_type": "stockout",
            "outlet_id": outlet.id,
            "outlet_name": outlet.name,
            "sku_id": sku.id,
            "sku_name": sku.name,
            "plan_date": str(body.plan_date),
            "daypart": alert.affected_daypart,
            "risk_level": alert.risk_level,
            "shortage_qty": _format_float(alert.shortage_qty),
            "coverage_pct": _format_float(alert.coverage_pct),
            "reason": alert.reason,
        }
        _message_text = _localize_message_text(
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
            raise HTTPException(status_code=404, detail="No replenishment recommendation found for this SKU/date")

        line = matching_lines[0]
        ingredient = line.ingredient
        unit = ingredient.unit if ingredient else "units"
        evidence = {
            "context_type": "replenishment",
            "outlet_id": outlet.id,
            "outlet_name": outlet.name,
            "sku_id": sku.id,
            "sku_name": sku.name,
            "plan_date": str(body.plan_date),
            "ingredient_name": ingredient.name if ingredient else "Unknown ingredient",
            "stock_on_hand": _format_float(line.stock_on_hand),
            "unit": unit,
            "need_qty": _format_float(line.need_qty),
            "reorder_qty": _format_float(line.reorder_qty),
            "urgency": line.urgency,
            "driving_skus": line.driving_skus or [],
        }
        _message_text = _localize_message_text(
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

    explanation = _call_grounded_explanation(language, ctx, evidence)
    return ExplainPlanResponse(
        explanation=explanation,
        context_type=ctx,
        outlet_name=outlet.name,
        sku_name=sku.name,
        evidence=evidence,
        source_type="llm_rephrased",
    )


@router.post("/copilot/daily-brief", response_model=DailyBriefResponse)
def generate_daily_brief(body: DailyBriefRequest, db: Session = Depends(get_db)):
    brief_date = body.brief_date
    language = _normalize_language(body.language)

    fc_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_date == brief_date)
        .order_by(desc(ForecastRun.created_at), desc(ForecastRun.id))
        .first()
    )
    if not fc_run:
        raise HTTPException(status_code=404, detail="Forecast run not found for daily brief date")
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
    _message_text = _localize_message_text(
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

    brief = _validate_daily_brief_text(_invoke_llm(prompt, max_tokens=900))
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
    def llm(
        prompt,
        _text="",
        max_tokens=900,
        response_format=None,
    ):
        return _invoke_llm(
            f"{_language_prompt_prefix(language)}\n\n{prompt}",
            _text,
            max_tokens=max_tokens,
            response_format=response_format,
        )
    try:
        payload = generate_daily_actions(body.target_date, body.top_n, db, llm, language)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return DailyActionsResponse(
        date=payload["date"],
        brief=payload["brief"],
        top_actions=payload["top_actions"],
        prep_actions=payload["prep_actions"],
        reorder_actions=payload["reorder_actions"],
        risk_warnings=payload["risk_warnings"],
        rebalance_suggestions=payload["rebalance_suggestions"],
    )
