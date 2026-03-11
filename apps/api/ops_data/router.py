"""
Ops data router — Task 11 (Acknowledgement API)
PATCH /plans/prep/{id}/lines/{line_id}
POST  /plans/prep/{id}/approve
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import PrepPlan, PrepPlanLine, AuditEvent

router = APIRouter()


class LineEditRequest(BaseModel):
    edited_units: int
    user_id: Optional[str] = "system"


class ApproveRequest(BaseModel):
    approved_by: str = "ops-manager"


class PrepPlanLineOut(BaseModel):
    id: int
    plan_id: int
    outlet_id: int
    sku_id: int
    daypart: str
    recommended_units: int
    edited_units: Optional[int]
    current_stock: int
    status: str
    model_config = {"from_attributes": True}


class PrepPlanOut(BaseModel):
    id: int
    plan_date: str
    status: str
    approved_by: Optional[str]
    lines: list[PrepPlanLineOut]
    model_config = {"from_attributes": True}


# ─── GET prep plan ────────────────────────────────────────────────────────────

@router.get("/plans/prep/{plan_id}", response_model=PrepPlanOut)
def get_prep_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(PrepPlan).filter(PrepPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="PrepPlan not found")
    return PrepPlanOut(
        id=plan.id,
        plan_date=str(plan.plan_date),
        status=plan.status,
        approved_by=plan.approved_by,
        lines=[PrepPlanLineOut.model_validate(l) for l in plan.lines],
    )


# ─── Edit a prep plan line ─────────────────────────────────────────────────────

@router.patch("/plans/prep/{plan_id}/lines/{line_id}", response_model=PrepPlanLineOut)
def edit_prep_line(
    plan_id: int,
    line_id: int,
    body: LineEditRequest,
    db: Session = Depends(get_db),
):
    plan = db.query(PrepPlan).filter(PrepPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="PrepPlan not found")
    if plan.status == "approved":
        raise HTTPException(status_code=409, detail="Cannot edit an approved plan")

    line = db.query(PrepPlanLine).filter(
        PrepPlanLine.id == line_id,
        PrepPlanLine.plan_id == plan_id,
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="PrepPlanLine not found")

    if body.edited_units < 0:
        raise HTTPException(status_code=422, detail="edited_units must be >= 0")

    before_value = {"edited_units": line.edited_units, "status": line.status}
    line.edited_units = body.edited_units
    line.status = "edited"

    audit = AuditEvent(
        event_type="prep_line_edited",
        entity_type="PrepPlanLine",
        entity_id=line.id,
        before_value=before_value,
        after_value={"edited_units": body.edited_units, "status": "edited"},
        user_id=body.user_id,
    )
    db.add(audit)
    db.commit()
    db.refresh(line)
    return line


# ─── Approve prep plan ─────────────────────────────────────────────────────────

@router.post("/plans/prep/{plan_id}/approve", response_model=PrepPlanOut)
def approve_prep_plan(
    plan_id: int,
    body: ApproveRequest,
    db: Session = Depends(get_db),
):
    plan = db.query(PrepPlan).filter(PrepPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="PrepPlan not found")
    if plan.status == "approved":
        raise HTTPException(status_code=409, detail="Plan is already approved")

    plan.status = "approved"
    plan.approved_by = body.approved_by
    plan.approved_at = datetime.utcnow()

    audit = AuditEvent(
        event_type="prep_plan_approved",
        entity_type="PrepPlan",
        entity_id=plan.id,
        before_value={"status": "draft"},
        after_value={"status": "approved", "approved_by": body.approved_by},
        user_id=body.approved_by,
    )
    db.add(audit)
    db.commit()
    db.refresh(plan)

    return PrepPlanOut(
        id=plan.id,
        plan_date=str(plan.plan_date),
        status=plan.status,
        approved_by=plan.approved_by,
        lines=[PrepPlanLineOut.model_validate(l) for l in plan.lines],
    )
