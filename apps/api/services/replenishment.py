"""
Replenishment service — calculates ingredient needs and shortages
"""
from datetime import date
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from db.models import ReplenishmentPlan, ReplenishmentPlanLine, Ingredient, RecipeBOM


def calculate_replenishment(
    prep_recommendations: List[Dict[str, Any]],
    db: Session,
) -> List[Dict[str, Any]]:
    """
    Calculate ingredient replenishment needs based on prep recommendations.

    Args:
        prep_recommendations: List of prep recommendations with sku_id and recommended_prep
        db: Database session

    Returns:
        List of replenishment recommendations
    """
    ingredient_needs = {}

    # Aggregate ingredient requirements across all prep recommendations
    for rec in prep_recommendations:
        sku_id = rec["sku_id"]
        recommended_prep = rec["recommended_prep"]

        # Get BOM for this SKU
        bom_lines = db.query(RecipeBOM).filter(RecipeBOM.sku_id == sku_id).all()

        for bom in bom_lines:
            ingredient_id = bom.ingredient_id
            required_qty = recommended_prep * bom.quantity_per_unit

            if ingredient_id not in ingredient_needs:
                ingredient_needs[ingredient_id] = {
                    "ingredient_id": ingredient_id,
                    "required_qty": 0,
                    "driving_skus": [],
                }

            ingredient_needs[ingredient_id]["required_qty"] += required_qty
            if sku_id not in ingredient_needs[ingredient_id]["driving_skus"]:
                ingredient_needs[ingredient_id]["driving_skus"].append(sku_id)

    # Calculate shortages and recommendations
    replenishments = []
    for ingredient_id, needs in ingredient_needs.items():
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            continue

        required_qty = needs["required_qty"]
        current_stock = ingredient.stock_on_hand
        shortage_qty = max(0, required_qty - current_stock)

        # Determine urgency
        if shortage_qty > 0:
            if shortage_qty / required_qty > 0.5:  # More than 50% shortage
                urgency = "critical"
            elif shortage_qty / required_qty > 0.2:  # More than 20% shortage
                urgency = "high"
            else:
                urgency = "medium"
        else:
            urgency = "low"

        # Calculate reorder quantity (simple: shortage + buffer)
        reorder_qty = shortage_qty * 1.1  # 10% buffer

        replenishments.append({
            "ingredient_id": ingredient_id,
            "ingredient_name": ingredient.name,
            "required_qty": round(required_qty, 2),
            "current_stock": round(current_stock, 2),
            "shortage_qty": round(shortage_qty, 2),
            "reorder_qty": round(reorder_qty, 2),
            "urgency": urgency,
            "driving_skus": needs["driving_skus"],
            "unit": ingredient.unit,
        })

    return replenishments


def save_replenishment_plan(
    plan_date: date,
    replenishments: List[Dict[str, Any]],
    db: Session,
) -> ReplenishmentPlan:
    """Save replenishment plan to database"""
    plan = ReplenishmentPlan(plan_date=plan_date, status="draft")
    db.add(plan)
    db.flush()

    for repl in replenishments:
        line = ReplenishmentPlanLine(
            plan_id=plan.id,
            ingredient_id=repl["ingredient_id"],
            need_qty=repl["required_qty"],
            stock_on_hand=repl["current_stock"],
            reorder_qty=repl["reorder_qty"],
            urgency=repl["urgency"],
            driving_skus=repl["driving_skus"],
            rationale_json={
                "shortage_qty": repl["shortage_qty"],
                "unit": repl["unit"],
            },
        )
        db.add(line)

    db.commit()
    db.refresh(plan)
    return plan