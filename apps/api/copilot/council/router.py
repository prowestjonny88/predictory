from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from copilot import llm as copilot_llm
from db.database import get_db
from db.models import DecisionAuditEvent, ForecastRun, Outlet, PrepPlanLine, ReplenishmentPlan, SKU
from planning.replenishment import recommend_replenishment
from services.uncertainty import band_for_prep_line

from .graph import build_council_review
from .schemas import (
    CouncilConfirmRequest,
    CouncilConfirmResponse,
    CouncilLineChange,
    CouncilReviewRequest,
    CouncilReviewResponse,
    CouncilReviewWithNoteRequest,
    CouncilReviewWithNoteResponse,
)
from .validators import validate_selected_prep

router = APIRouter()
logger = logging.getLogger(__name__)


def _refresh_replenishment_for_date(plan_date, db: Session) -> Optional[ReplenishmentPlan]:
    for plan in db.query(ReplenishmentPlan).filter(ReplenishmentPlan.plan_date == plan_date).all():
        db.delete(plan)
    db.commit()
    return recommend_replenishment(plan_date, db)


@router.post("/copilot/council/review", response_model=CouncilReviewResponse)
def review_council(body: CouncilReviewRequest, db: Session = Depends(get_db)):
    logger.info(
        "[council-review] recommendation_id=%s language=%s",
        body.recommendation_id,
        body.language,
    )
    return build_council_review(
        recommendation_id=body.recommendation_id,
        db=db,
        llm_fn=copilot_llm.invoke_llm,
        language=body.language,
    )


@router.post("/copilot/council/review-with-note", response_model=CouncilReviewWithNoteResponse)
def review_council_with_note(body: CouncilReviewWithNoteRequest, db: Session = Depends(get_db)):
    logger.info(
        "[council-review-with-note] recommendation_id=%s language=%s adjustment_outlet=%s adjustment_daypart=%s adjustment_category=%s",
        body.recommendation_id,
        body.language,
        body.parsed_adjustment.outlet_id,
        body.parsed_adjustment.daypart,
        body.parsed_adjustment.sku_category,
    )
    before = build_council_review(
        recommendation_id=body.recommendation_id,
        db=db,
        llm_fn=copilot_llm.invoke_llm,
        language=body.language,
    )
    after = build_council_review(
        recommendation_id=body.recommendation_id,
        db=db,
        llm_fn=copilot_llm.invoke_llm,
        manager_adjustment=body.parsed_adjustment,
        language=body.language,
    )
    return CouncilReviewWithNoteResponse(before_review=before, after_review=after)


@router.post("/copilot/council/confirm", response_model=CouncilConfirmResponse)
def confirm_council_recommendation(body: CouncilConfirmRequest, db: Session = Depends(get_db)):
    logger.info(
        "[council-confirm] recommendation_id=%s selected_prep=%s language=%s has_manager_adjustment=%s",
        body.recommendation_id,
        body.selected_prep,
        body.language,
        body.manager_adjustment is not None,
    )
    review = build_council_review(
        recommendation_id=body.recommendation_id,
        db=db,
        llm_fn=copilot_llm.invoke_llm,
        manager_adjustment=body.manager_adjustment,
        language=body.language,
    )
    selected_candidate = validate_selected_prep(body.selected_prep, review.candidate_quantities)

    # Re-load via the review's recommendation ID so the server, not the client, owns mutation state.
    line_id = int(review.recommendation_id)
    prep_line = db.query(PrepPlanLine).filter(PrepPlanLine.id == line_id).first()
    if not prep_line or not prep_line.plan:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    forecast_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_date == prep_line.plan.plan_date)
        .order_by(desc(ForecastRun.created_at), desc(ForecastRun.id))
        .first()
    )
    if not forecast_run:
        raise HTTPException(status_code=422, detail="Forecast run is required for council confirmation")
    forecast_line = next(
        (
            candidate
            for candidate in forecast_run.lines
            if candidate.outlet_id == prep_line.outlet_id and candidate.sku_id == prep_line.sku_id
        ),
        None,
    )
    outlet = db.query(Outlet).filter(Outlet.id == prep_line.outlet_id).first()
    sku = db.query(SKU).filter(SKU.id == prep_line.sku_id).first()
    if not forecast_line or not outlet or not sku:
        raise HTTPException(status_code=422, detail="Forecast, outlet, and SKU evidence are required for confirmation")

    before_prep = prep_line.edited_units if prep_line.edited_units is not None else prep_line.recommended_units
    prep_line.edited_units = body.selected_prep
    prep_line.status = "edited"
    db.add(prep_line)

    band = band_for_prep_line(prep_line=prep_line, forecast_line=forecast_line, sku=sku, outlet_code=outlet.code)
    compact_summary = {
        "source": "agent_council",
        "selected_prep": body.selected_prep,
        "selected_candidate_source": selected_candidate.source,
        "agent_consensus": review.judge_recommendation.agent_consensus,
        "primary_conflict": review.judge_recommendation.primary_conflict,
    }
    event = DecisionAuditEvent(
        forecast_run_id=forecast_run.forecast_run_id,
        model_version=forecast_run.model_version,
        engine_name=forecast_run.engine_name,
        outlet_id=prep_line.outlet_id,
        sku_id=prep_line.sku_id,
        daypart=prep_line.daypart,
        p10=band.p10,
        p50=band.p50,
        p90=band.p90,
        recommended_prep=prep_line.recommended_units,
        final_prep=body.selected_prep,
        operator_action="edited",
        operator_reason=body.operator_reason,
        gemini_note_adjustment_applied=body.manager_adjustment is not None,
        gemini_note_summary=json.dumps(compact_summary),
    )
    db.add(event)
    db.flush()
    audit_event_id = event.id
    db.commit()

    warnings: list[str] = []
    replenishment_plan = None
    try:
        replenishment_plan = _refresh_replenishment_for_date(prep_line.plan.plan_date, db)
    except Exception as exc:
        warnings.append(f"Replenishment refresh failed after prep edit; regenerate replenishment. Detail: {exc}")
    line_change = CouncilLineChange(
        line_id=prep_line.id,
        outlet_name=outlet.name,
        sku_name=sku.name,
        daypart=prep_line.daypart,
        before_prep=before_prep,
        after_prep=body.selected_prep,
    )
    return CouncilConfirmResponse(
        forecast_run_id=forecast_run.forecast_run_id,
        status="applied",
        message="Agent Council recommendation applied after explicit confirmation.",
        application_mode="prep_edit_only",
        selected_candidate_source=selected_candidate.source,
        audit_event_ids=[audit_event_id],
        replenishment_plan_id=replenishment_plan.id if replenishment_plan else None,
        warnings=warnings,
        line_changes=[line_change],
        council_review=review,
    )
