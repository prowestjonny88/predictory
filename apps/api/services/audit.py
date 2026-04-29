"""
Audit service — logs decisions and changes
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from db.models import AuditEvent, DecisionAuditEvent


def log_decision_audit(
    forecast_run_id: str,
    model_version: str,
    engine_name: str,
    outlet_id: int,
    sku_id: int,
    daypart: str,
    p10: float,
    p50: float,
    p90: float,
    recommended_prep: int,
    final_prep: int,
    operator_action: str,
    operator_reason: str,
    gemini_note_adjustment_applied: bool = False,
    gemini_note_summary: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = None,
) -> DecisionAuditEvent:
    """
    Log a decision audit event
    """
    event = DecisionAuditEvent(
        forecast_run_id=forecast_run_id,
        model_version=model_version,
        engine_name=engine_name,
        outlet_id=outlet_id,
        sku_id=sku_id,
        daypart=daypart,
        p10=p10,
        p50=p50,
        p90=p90,
        recommended_prep=recommended_prep,
        final_prep=final_prep,
        operator_action=operator_action,
        operator_reason=operator_reason,
        gemini_note_adjustment_applied=gemini_note_adjustment_applied,
        gemini_note_summary=gemini_note_summary,
    )

    if db:
        db.add(event)
        db.commit()
        db.refresh(event)

    return event


def log_forecast_adjustment(
    forecast_run_id: int,
    line_id: int,
    before_values: dict,
    after_values: dict,
    user_id: Optional[str] = None,
    db: Session = None,
) -> AuditEvent:
    """
    Log forecast line adjustment
    """
    event = AuditEvent(
        event_type="forecast_line_adjusted",
        entity_type="ForecastLine",
        entity_id=line_id,
        before_value=before_values,
        after_value=after_values,
        user_id=user_id,
    )

    if db:
        db.add(event)
        db.commit()
        db.refresh(event)

    return event


def get_audit_events(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    db: Session = None,
) -> List[AuditEvent]:
    """
    Retrieve audit events with optional filtering
    """
    if not db:
        return []

    query = db.query(AuditEvent)

    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditEvent.entity_id == entity_id)
    if user_id:
        query = query.filter(AuditEvent.user_id == user_id)

    return query.order_by(AuditEvent.created_at.desc()).limit(limit).all()