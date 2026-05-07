from __future__ import annotations

from fastapi import HTTPException

from .schemas import CandidateQuantity, JudgeRecommendation


def candidate_by_source(candidates: list[CandidateQuantity], source: str) -> CandidateQuantity | None:
    return next((candidate for candidate in candidates if candidate.source == source), None)


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
    allowed_quantities = {candidate.quantity for candidate in candidates}
    allowed_sources = {candidate.source for candidate in candidates}
    recommended_prep = int(raw["recommended_prep"])
    selected_source = str(raw["selected_candidate_source"])
    if recommended_prep not in allowed_quantities:
        raise ValueError("Judge selected a non-candidate prep quantity")
    if selected_source not in allowed_sources:
        raise ValueError("Judge selected an unknown candidate source")
    return JudgeRecommendation(
        recommended_prep=recommended_prep,
        selected_candidate_source=selected_source,
        requires_confirmation=bool(raw.get("requires_confirmation", True)),
        reasoning_summary=str(raw.get("reasoning_summary") or "Council selected a validated candidate."),
        primary_conflict=raw.get("primary_conflict"),
        agent_consensus=str(raw.get("agent_consensus") or "split"),  # type: ignore[arg-type]
        source="judge_synthesized",
    )

