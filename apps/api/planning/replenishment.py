"""
Ingredient replenishment logic — Task 7
recommend_replenishment(target_date, db) -> ReplenishmentPlan
"""
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from db.models import (
    Ingredient, RecipeBOM, PrepPlanLine, PrepPlan,
    ReplenishmentPlan, ReplenishmentPlanLine, SKU
)

URGENCY_CRITICAL = 0.50   # stock < 50% of need
URGENCY_HIGH     = 0.80   # stock < 80% of need
URGENCY_MEDIUM   = 1.00   # stock < 100% of need


def _classify_urgency(stock: float, need: float, lead_time_hours: int) -> str:
    if need <= 0:
        return "low"
    ratio = stock / need
    # Bump urgency if lead time > 24h
    lead_bump = lead_time_hours > 24
    if ratio < URGENCY_CRITICAL or (lead_bump and ratio < URGENCY_HIGH):
        return "critical"
    if ratio < URGENCY_HIGH or (lead_bump and ratio < URGENCY_MEDIUM):
        return "high"
    if ratio < URGENCY_MEDIUM:
        return "medium"
    return "low"


def recommend_replenishment(target_date: date, db: Session) -> ReplenishmentPlan:
    """
    For each ingredient, compute total need from prep plan, compare to stock, set urgency.
    """
    # Get or generate today's prep plan lines
    plan = (
        db.query(PrepPlan)
        .filter(PrepPlan.plan_date == target_date)
        .order_by(PrepPlan.created_at.desc())
        .first()
    )

    ingredient_need: dict[int, float] = {}
    ingredient_skus: dict[int, list[str]] = {}

    if plan:
        # Aggregate prep units per SKU across outlets and dayparts
        sku_total_prep: dict[int, float] = {}
        for line in plan.lines:
            qty = line.edited_units if line.edited_units is not None else line.recommended_units
            sku_total_prep[line.sku_id] = sku_total_prep.get(line.sku_id, 0) + qty

        # Map SKU prep to ingredient need using BOM
        bom_rows = db.query(RecipeBOM).all()
        skus_map = {s.id: s.name for s in db.query(SKU).all()}

        for bom in bom_rows:
            prep_qty = sku_total_prep.get(bom.sku_id, 0)
            if prep_qty == 0:
                continue
            need = prep_qty * bom.quantity_per_unit
            ingredient_need[bom.ingredient_id] = ingredient_need.get(bom.ingredient_id, 0) + need
            ingredient_skus.setdefault(bom.ingredient_id, [])
            sku_name = skus_map.get(bom.sku_id, f"SKU-{bom.sku_id}")
            if sku_name not in ingredient_skus[bom.ingredient_id]:
                ingredient_skus[bom.ingredient_id].append(sku_name)

    ingredients = db.query(Ingredient).filter(Ingredient.is_active == True).all()

    repl_plan = ReplenishmentPlan(plan_date=target_date, status="draft")
    db.add(repl_plan)
    db.flush()

    for ing in ingredients:
        need = ingredient_need.get(ing.id, 0.0)
        stock = ing.stock_on_hand
        reorder_qty = max(0.0, need - stock)
        urgency = _classify_urgency(stock, need, ing.supplier_lead_time_hours)

        rationale = {
            "formula": "need = Σ(prep_qty × recipe_qty_per_unit)",
            "total_need": round(need, 2),
            "stock_on_hand": stock,
            "reorder_qty": round(reorder_qty, 2),
            "lead_time_hours": ing.supplier_lead_time_hours,
        }

        line = ReplenishmentPlanLine(
            plan_id=repl_plan.id,
            ingredient_id=ing.id,
            need_qty=round(need, 3),
            stock_on_hand=stock,
            reorder_qty=round(reorder_qty, 3),
            urgency=urgency,
            driving_skus=ingredient_skus.get(ing.id, []),
            rationale_json=rationale,
        )
        db.add(line)

    db.commit()
    db.refresh(repl_plan)
    return repl_plan
