from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from .candidates import build_candidate_quantities
from .evidence import load_recommendation_context
from .prompts import JUDGE_SYNTHESIZER_PROMPT
from .schemas import (
    AgentArgument,
    AgentTraceItem,
    CandidateQuantity,
    CouncilReviewResponse,
    JudgeRecommendation,
    ParsedAdjustment,
)
from .trace import agent_trace_item, graph_step
from .validators import candidate_by_source, validate_judge

LLMFn = Callable[..., str]


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _severity_for_exposure(value: float) -> str:
    if value >= 500:
        return "critical"
    if value >= 200:
        return "high"
    if value > 0:
        return "medium"
    return "low"


def _build_agent_arguments(context: dict[str, Any], manager_adjustment: Optional[ParsedAdjustment]) -> tuple[list[AgentArgument], list[AgentTraceItem]]:
    p10 = context["p10"]
    p50 = context["p50"]
    p90 = context["p90"]
    stockout_exposure = context["stockout_exposure_rm"]
    waste_exposure = context["waste_exposure_rm"]
    replenishment = context["replenishment"]

    arguments: list[AgentArgument] = [
        AgentArgument(
            agent="Forecast Agent",
            stance="evidence",
            claim=f"Expected demand is {p50:.1f} units; busy-day demand may reach {p90:.1f}.",
            evidence={"low_demand": p10, "expected_demand": p50, "high_demand": p90, "source": "LightGBM"},
            suggested_candidate_source="expected_demand",
            severity="info",
            source="lightgbm",
        )
    ]

    stockout_stance = "increase_prep" if stockout_exposure >= waste_exposure and stockout_exposure > 0 else "hold"
    arguments.append(
        AgentArgument(
            agent="Stockout Guardian",
            stance=stockout_stance,
            claim=(
                f"Stockout exposure is RM {stockout_exposure:.2f}; higher prep may protect availability."
                if stockout_exposure > 0
                else "No material stockout exposure is visible for this recommendation."
            ),
            evidence={"stockout_exposure_rm": stockout_exposure, "high_demand": p90},
            suggested_candidate_source="stockout_guardrail",
            severity=_severity_for_exposure(stockout_exposure),  # type: ignore[arg-type]
            source="optimizer",
        )
    )

    waste_stance = "decrease_prep" if waste_exposure > stockout_exposure and waste_exposure > 0 else "caution"
    arguments.append(
        AgentArgument(
            agent="Waste Guardian",
            stance=waste_stance,
            claim=(
                f"Waste exposure is RM {waste_exposure:.2f}; conservative prep limits leftovers on quiet demand."
                if waste_exposure > 0
                else "No material waste exposure is visible for this recommendation."
            ),
            evidence={"waste_exposure_rm": waste_exposure, "low_demand": p10},
            suggested_candidate_source="waste_guardrail",
            severity=_severity_for_exposure(waste_exposure),  # type: ignore[arg-type]
            source="optimizer",
        )
    )

    top_shortage = next((item for item in replenishment if item.shortage_qty > 0), None)
    if top_shortage:
        claim = (
            f"{top_shortage.ingredient_name} is short by {top_shortage.shortage_qty:.2f} "
            f"{top_shortage.unit} for this prep level."
        )
        evidence = _model_dump(top_shortage)
        severity = top_shortage.urgency if top_shortage.urgency in {"low", "medium", "high", "critical"} else "medium"
    else:
        claim = "No ingredient shortage is visible for this prep level."
        evidence = {"shortage_qty": 0}
        severity = "low"
    arguments.append(
        AgentArgument(
            agent="Replenishment Agent",
            stance="reorder" if top_shortage else "hold",
            claim=claim,
            evidence=evidence,
            severity=severity,  # type: ignore[arg-type]
            source="rules_based",
        )
    )

    if manager_adjustment is not None:
        arguments.append(
            AgentArgument(
                agent="Manager Context Agent",
                stance="manager_context",
                claim=(
                    f"Manager note requests {manager_adjustment.suggested_adjustment_pct:+.1f}% for "
                    f"{manager_adjustment.sku_category} at {manager_adjustment.outlet_id} in the {manager_adjustment.daypart}."
                ),
                evidence=_model_dump(manager_adjustment),
                suggested_candidate_source="manager_note_adjusted",
                severity="medium",
                source="manager_note",
            )
        )

    trace_items = [
        agent_trace_item(
            agent=argument.agent,
            role=argument.stance,
            claim=argument.claim,
            evidence=argument.evidence,
            stance=argument.stance,
            severity=argument.severity,
            source=argument.source,
        )
        for argument in arguments
    ]
    return arguments, trace_items


def _fallback_judge(candidates: list[CandidateQuantity], reason: str) -> JudgeRecommendation:
    selected = candidate_by_source(candidates, "optimizer") or candidate_by_source(candidates, "expected_demand") or candidates[0]
    return JudgeRecommendation(
        recommended_prep=selected.quantity,
        selected_candidate_source=selected.source,
        requires_confirmation=True,
        reasoning_summary=f"Judge fallback selected the server-generated {selected.source} candidate. {reason}",
        primary_conflict="Judge LLM output was unavailable or invalid.",
        agent_consensus="split",
        source="fallback",
    )


def _run_judge(
    *,
    candidates: list[CandidateQuantity],
    arguments: list[AgentArgument],
    context: dict[str, Any],
    llm_fn: LLMFn,
) -> tuple[JudgeRecommendation, AgentTraceItem, str]:
    evidence = {
        "recommendation_id": context["recommendation_id"],
        "outlet_name": context["outlet_name"],
        "sku_name": context["sku_name"],
        "daypart": context["daypart"],
        "p10": context["p10"],
        "p50": context["p50"],
        "p90": context["p90"],
        "opening_stock": context["opening_stock"],
        "current_recommended_prep": context["current_recommended_prep"],
        "stockout_exposure_rm": context["stockout_exposure_rm"],
        "waste_exposure_rm": context["waste_exposure_rm"],
    }
    prompt = JUDGE_SYNTHESIZER_PROMPT.format(
        candidate_quantities_json=json.dumps([_model_dump(candidate) for candidate in candidates], indent=2),
        agent_arguments_json=json.dumps([_model_dump(argument) for argument in arguments], indent=2),
        evidence_json=json.dumps(evidence, indent=2),
    )
    try:
        raw = llm_fn(prompt, "", max_tokens=700, response_format={"type": "json_object"})
        judge = validate_judge(_extract_json_object(raw), candidates)
        status = "ok"
    except Exception as exc:
        judge = _fallback_judge(candidates, str(exc))
        status = "fallback"

    trace = agent_trace_item(
        agent="Judge Agent",
        role="synthesizer",
        claim=judge.reasoning_summary,
        evidence={
            "recommended_prep": judge.recommended_prep,
            "selected_candidate_source": judge.selected_candidate_source,
            "agent_consensus": judge.agent_consensus,
            "primary_conflict": judge.primary_conflict,
        },
        stance="hold",
        severity="medium" if judge.requires_confirmation else "info",
        source=judge.source,
    )
    return judge, trace, status


def build_council_review(
    *,
    recommendation_id: str,
    db: Session,
    llm_fn: LLMFn,
    manager_adjustment: Optional[ParsedAdjustment] = None,
    language: str = "en",
) -> CouncilReviewResponse:
    graph_trace: list[dict[str, Any]] = []
    context = load_recommendation_context(recommendation_id, db, manager_adjustment)
    graph_trace = graph_step(graph_trace, "load_recommendation_context", recommendation_id=recommendation_id)

    candidates = build_candidate_quantities(
        p10=context["p10"],
        p50=context["p50"],
        p90=context["p90"],
        opening_stock=context["opening_stock"],
        current_recommended_prep=context["current_recommended_prep"],
        batch_size=context["batch_size"],
        manager_adjustment=manager_adjustment,
    )
    graph_trace = graph_step(graph_trace, "build_candidate_quantities", candidate_count=len(candidates))

    arguments, agent_trace = _build_agent_arguments(context, manager_adjustment)
    graph_trace = graph_step(graph_trace, "build_agent_arguments", argument_count=len(arguments))

    judge, judge_trace, judge_status = _run_judge(
        candidates=candidates,
        arguments=arguments,
        context=context,
        llm_fn=llm_fn,
    )
    agent_trace.append(judge_trace)
    graph_trace = graph_step(graph_trace, "judge_synthesizer", status=judge_status, selected_prep=judge.recommended_prep)
    graph_trace = graph_step(graph_trace, "finalize_council_review", language=language)

    return CouncilReviewResponse(
        recommendation_id=context["recommendation_id"],
        plan_id=context["plan_id"],
        outlet_name=context["outlet_name"],
        sku_name=context["sku_name"],
        daypart=context["daypart"],
        current_recommended_prep=context["current_recommended_prep"],
        candidate_quantities=candidates,
        agent_arguments=arguments,
        agent_trace=agent_trace,
        judge_recommendation=judge,
        graph_trace=graph_trace,
    )

