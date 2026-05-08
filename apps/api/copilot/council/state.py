from __future__ import annotations

from datetime import date
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from .schemas import ParsedAdjustment


class CouncilState(TypedDict, total=False):
    db: Session
    llm_fn: Any
    language: str
    manager_adjustment: ParsedAdjustment | None
    context: dict[str, Any]
    recommendation_id: str
    plan_id: int
    target_date: date
    forecast_run_id: str
    model_version: str
    engine_name: str
    outlet_id: int
    outlet_name: str
    sku_id: int
    sku_name: str
    sku_category: str
    daypart: str
    p10: float
    p50: float
    p90: float
    opening_stock: float
    current_recommended_prep: int
    batch_size: int
    waste_cost: float
    stockout_cost: float
    stockout_exposure_rm: float
    waste_exposure_rm: float
    reason_summary: str
    replenishment: list[dict[str, Any]]
    manager_note: str | None
    candidate_quantities: list[dict[str, Any]]
    agent_arguments: list[dict[str, Any]]
    agent_trace: list[dict[str, Any]]
    judge_recommendation: dict[str, Any]
    graph_trace: list[dict[str, Any]]

