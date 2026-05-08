from __future__ import annotations

import math
from typing import Any

from .schemas import CandidateQuantity, ParsedAdjustment


def _round_up_to_batch(value: float, batch_size: int) -> int:
    value = max(0.0, float(value))
    if batch_size <= 1:
        return int(math.ceil(value))
    return int(math.ceil(value / batch_size) * batch_size)


def _add_candidate(
    candidates: list[CandidateQuantity],
    *,
    quantity: int,
    source: str,
    reason: str,
    evidence: dict[str, Any],
) -> None:
    quantity = max(0, int(quantity))
    existing = next((candidate for candidate in candidates if candidate.quantity == quantity), None)
    if existing:
        if source not in existing.alternate_sources and source != existing.source:
            existing.alternate_sources.append(source)
            existing.reason = f"{existing.reason} Also matches {source}: {reason}"
        return
    candidates.append(
        CandidateQuantity(
            quantity=quantity,
            source=source,  # type: ignore[arg-type]
            reason=reason,
            evidence=evidence,
        )
    )


def build_candidate_quantities(
    *,
    p10: float,
    p50: float,
    p90: float,
    opening_stock: float,
    optimizer_recommended_prep: int,
    current_plan_prep: int | None = None,
    batch_size: int,
    manager_adjustment: ParsedAdjustment | None = None,
) -> list[CandidateQuantity]:
    candidates: list[CandidateQuantity] = []
    current_prep = int(current_plan_prep if current_plan_prep is not None else optimizer_recommended_prep)

    _add_candidate(
        candidates,
        quantity=max(0, int(optimizer_recommended_prep)),
        source="optimizer",
        reason="Original optimizer-backed prep for this line.",
        evidence={"optimizer_recommended_prep": optimizer_recommended_prep},
    )

    if current_plan_prep is not None and int(current_plan_prep) != int(optimizer_recommended_prep):
        _add_candidate(
            candidates,
            quantity=max(0, int(current_plan_prep)),
            source="current_plan",
            reason="Current plan quantity after a prior human or council edit.",
            evidence={
                "current_plan_prep": current_plan_prep,
                "optimizer_recommended_prep": optimizer_recommended_prep,
            },
        )

    expected = _round_up_to_batch(p50 - opening_stock, batch_size)
    _add_candidate(
        candidates,
        quantity=expected,
        source="expected_demand",
        reason="Covers expected demand after opening stock.",
        evidence={"p50": p50, "opening_stock": opening_stock, "batch_size": batch_size},
    )

    stockout = _round_up_to_batch(p90 - opening_stock, batch_size)
    _add_candidate(
        candidates,
        quantity=stockout,
        source="stockout_guardrail",
        reason="Covers busy-day demand after opening stock.",
        evidence={"p90": p90, "opening_stock": opening_stock, "batch_size": batch_size},
    )

    waste_base = p10 - opening_stock
    if waste_base <= 0:
        waste_base = p50 - opening_stock
    waste = _round_up_to_batch(waste_base, batch_size)
    _add_candidate(
        candidates,
        quantity=waste,
        source="waste_guardrail",
        reason="Conservative prep option to limit leftovers on a quieter day.",
        evidence={"p10": p10, "p50": p50, "opening_stock": opening_stock, "batch_size": batch_size},
    )

    if manager_adjustment is not None:
        bounded_pct = max(-50.0, min(50.0, float(manager_adjustment.suggested_adjustment_pct)))
        adjusted = _round_up_to_batch(current_prep * (1 + bounded_pct / 100.0), batch_size)
        _add_candidate(
            candidates,
            quantity=adjusted,
            source="manager_note_adjusted",
            reason="Manager-note adjusted prep, bounded to +/-50%.",
            evidence={
                "base_prep": current_prep,
                "adjustment_pct": bounded_pct,
                "reason": manager_adjustment.reason,
                "batch_size": batch_size,
            },
        )

    return candidates

