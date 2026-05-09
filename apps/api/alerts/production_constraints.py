"""
Production constraint alert logic.

These alerts represent ingredient shortages against the current prep plan.
They are intentionally separate from finished-goods stockout alerts.
"""
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from db.models import Ingredient, PrepPlan, RecipeBOM, SKU
from planning.replenishment import _classify_urgency


@dataclass
class ProductionConstraintAlert:
    ingredient_id: int
    ingredient_name: str
    required_qty: float
    stock_on_hand: float
    shortage_qty: float
    reorder_qty: float
    unit: str
    urgency: str
    coverage_pct: float
    driving_skus: list[str]
    reason: str


def detect_production_constraints(target_date: date, db: Session) -> list[ProductionConstraintAlert]:
    prep_plan = (
        db.query(PrepPlan)
        .filter(PrepPlan.plan_date == target_date)
        .order_by(PrepPlan.created_at.desc(), PrepPlan.id.desc())
        .first()
    )
    if not prep_plan:
        return []

    sku_total_prep: dict[int, float] = {}
    for line in prep_plan.lines:
        qty = line.edited_units if line.edited_units is not None else line.recommended_units
        sku_total_prep[line.sku_id] = sku_total_prep.get(line.sku_id, 0.0) + max(0.0, float(qty or 0))

    if not sku_total_prep:
        return []

    skus_map = {sku.id: sku.name for sku in db.query(SKU).all()}
    ingredient_need: dict[int, float] = {}
    ingredient_skus: dict[int, list[str]] = {}
    for bom in db.query(RecipeBOM).all():
        prep_qty = sku_total_prep.get(bom.sku_id, 0.0)
        if prep_qty <= 0:
            continue
        need = prep_qty * float(bom.quantity_per_unit or 0)
        if need <= 0:
            continue
        ingredient_need[bom.ingredient_id] = ingredient_need.get(bom.ingredient_id, 0.0) + need
        sku_name = skus_map.get(bom.sku_id, f"SKU-{bom.sku_id}")
        names = ingredient_skus.setdefault(bom.ingredient_id, [])
        if sku_name not in names:
            names.append(sku_name)

    alerts: list[ProductionConstraintAlert] = []
    ingredients = {ingredient.id: ingredient for ingredient in db.query(Ingredient).filter(Ingredient.is_active == True).all()}
    for ingredient_id, required_qty in ingredient_need.items():
        ingredient = ingredients.get(ingredient_id)
        if not ingredient:
            continue
        stock = float(ingredient.stock_on_hand or 0.0)
        shortage = max(0.0, required_qty - stock)
        if shortage <= 0:
            continue
        urgency = _classify_urgency(stock, required_qty, ingredient.supplier_lead_time_hours)
        coverage_pct = (stock / required_qty * 100.0) if required_qty > 0 else 100.0
        alerts.append(
            ProductionConstraintAlert(
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                required_qty=round(required_qty, 3),
                stock_on_hand=round(stock, 3),
                shortage_qty=round(shortage, 3),
                reorder_qty=round(shortage, 3),
                unit=ingredient.unit,
                urgency=urgency,
                coverage_pct=round(coverage_pct, 1),
                driving_skus=ingredient_skus.get(ingredient.id, []),
                reason=(
                    f"{ingredient.name} stock covers only {coverage_pct:.0f}% "
                    "of planned production need"
                ),
            )
        )

    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda item: (urgency_order.get(item.urgency, 9), -item.shortage_qty))
    return alerts
