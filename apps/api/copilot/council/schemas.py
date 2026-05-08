from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


CouncilSource = Literal[
    "lightgbm",
    "optimizer",
    "rules_based",
    "llm_rephrased",
    "judge_synthesized",
    "fallback",
    "manager_note",
]


class ParsedAdjustment(BaseModel):
    # Compatibility note: v1 manager-note parsing stores the outlet display name
    # in this field. TODO v2: rename to outlet_name and add numeric outlet_id.
    outlet_id: str
    daypart: str
    sku_category: str
    suggested_adjustment_pct: float
    reason: str
    requires_confirmation: bool = True
    parse_source: Literal["llm_validated"]
    uncertainty_reason: Optional[str] = None


class CouncilReviewRequest(BaseModel):
    recommendation_id: str
    language: str = "en"


class CouncilReviewWithNoteRequest(BaseModel):
    recommendation_id: str
    parsed_adjustment: ParsedAdjustment
    original_note: Optional[str] = None
    language: str = "en"


class CouncilConfirmRequest(BaseModel):
    recommendation_id: str
    selected_prep: int
    manager_adjustment: Optional[ParsedAdjustment] = None
    operator_reason: str
    language: str = "en"


class CandidateQuantity(BaseModel):
    quantity: int
    source: Literal[
        "expected_demand",
        "optimizer",
        "current_plan",
        "stockout_guardrail",
        "waste_guardrail",
        "manager_note_adjusted",
    ]
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    alternate_sources: list[str] = Field(default_factory=list)


class AgentTraceItem(BaseModel):
    agent: str
    role: str
    claim: str
    stance: Optional[str] = None
    severity: Literal["info", "low", "medium", "high", "critical"] = "info"
    source: CouncilSource = "rules_based"
    evidence: dict[str, Any] = Field(default_factory=dict)


class AgentArgument(BaseModel):
    agent: str
    stance: Literal[
        "increase_prep",
        "decrease_prep",
        "hold",
        "reorder",
        "caution",
        "evidence",
        "manager_context",
    ]
    claim: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    suggested_candidate_source: Optional[str] = None
    severity: Literal["info", "low", "medium", "high", "critical"] = "info"
    source: CouncilSource = "rules_based"


class JudgeRecommendation(BaseModel):
    recommended_prep: int
    selected_candidate_source: str
    requires_confirmation: bool
    reasoning_summary: str
    primary_conflict: Optional[str] = None
    agent_consensus: Literal["aligned", "split", "contested"]
    source: Literal["judge_synthesized", "fallback"] = "judge_synthesized"


class ReplenishmentItem(BaseModel):
    ingredient_id: str
    ingredient_name: str
    required_qty: float
    current_stock: float
    shortage_qty: float
    reorder_qty: float
    unit: str
    urgency: str


class CouncilReviewResponse(BaseModel):
    recommendation_id: str
    plan_id: Optional[int] = None
    outlet_name: str
    sku_name: str
    daypart: str
    current_recommended_prep: int
    candidate_quantities: list[CandidateQuantity]
    agent_arguments: list[AgentArgument]
    agent_trace: list[AgentTraceItem]
    judge_recommendation: JudgeRecommendation
    graph_trace: list[dict[str, Any]] = Field(default_factory=list)
    source_type: Literal["agent_council"] = "agent_council"


class CouncilReviewWithNoteResponse(BaseModel):
    before_review: CouncilReviewResponse
    after_review: CouncilReviewResponse
    source_type: Literal["agent_council"] = "agent_council"


class CouncilLineChange(BaseModel):
    line_id: int
    outlet_name: str
    sku_name: str
    daypart: str
    before_prep: int
    after_prep: int


class CouncilConfirmResponse(BaseModel):
    forecast_run_id: str
    status: Literal["applied"]
    message: str
    application_mode: Literal["prep_edit_only"]
    selected_candidate_source: str
    audit_event_ids: list[int]
    replenishment_plan_id: Optional[int]
    warnings: list[str] = Field(default_factory=list)
    line_changes: list[CouncilLineChange]
    council_review: CouncilReviewResponse

