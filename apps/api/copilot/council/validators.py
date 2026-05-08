from __future__ import annotations

from fastapi import HTTPException

from .schemas import CandidateQuantity, JudgeRecommendation


def candidate_by_source(candidates: list[CandidateQuantity], source: str) -> CandidateQuantity | None:
    return next((candidate for candidate in candidates if candidate.source == source), None)


def candidate_for_judge_output(
    recommended_prep: int,
    selected_source: str,
    candidates: list[CandidateQuantity],
) -> CandidateQuantity:
    for candidate in candidates:
        if candidate.quantity == recommended_prep and candidate.source == selected_source:
            return candidate
    raise ValueError("Judge selected a mismatched quantity/source pair")


def validate_selected_prep(selected_prep: int, candidates: list[CandidateQuantity]) -> CandidateQuantity:
    for candidate in candidates:
        if candidate.quantity == selected_prep:
            return candidate
    allowed = ", ".join(str(candidate.quantity) for candidate in candidates)
    raise HTTPException(
        status_code=422,
        detail=f"Selected prep must match a server-generated council candidate. Allowed: {allowed}",
    )


def validate_judge(raw: dict, candidates: list[CandidateQuantity]) -> JudgeRecommendation:
    recommended_prep = int(raw["recommended_prep"])
    selected_source = str(raw["selected_candidate_source"])
    candidate_for_judge_output(recommended_prep, selected_source, candidates)
    consensus = str(raw.get("agent_consensus") or "split")
    if consensus not in {"aligned", "split", "contested"}:
        raise ValueError("Judge selected an invalid agent_consensus")
    return JudgeRecommendation(
        recommended_prep=recommended_prep,
        selected_candidate_source=selected_source,
        requires_confirmation=bool(raw.get("requires_confirmation", True)),
        reasoning_summary=str(raw.get("reasoning_summary") or "Council selected a validated candidate."),
        primary_conflict=raw.get("primary_conflict"),
        agent_consensus=consensus,  # type: ignore[arg-type]
        source="judge_synthesized",
    )

