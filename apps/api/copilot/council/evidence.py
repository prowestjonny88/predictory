from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from db.models import ForecastRun, Ingredient, Outlet, PrepPlanLine, RecipeBOM, SKU
from services.optimizer import calculate_optimal_prep
from services.uncertainty import band_for_prep_line

from .schemas import ParsedAdjustment, ReplenishmentItem


def sku_unit_cost(sku: SKU, db: Session) -> float:
    bom_rows = db.query(RecipeBOM).filter(RecipeBOM.sku_id == sku.id).all()
    cost = 0.0
    for bom in bom_rows:
        ingredient = db.query(Ingredient).filter(Ingredient.id == bom.ingredient_id).first()
        if ingredient:
            cost += float(ingredient.cost_per_unit or 0) * float(bom.quantity_per_unit or 0)
    if cost <= 0:
        raise HTTPException(status_code=422, detail=f"Recipe BOM cost is missing for SKU '{sku.code}'")
    return round(cost, 2)


def ingredient_impact_for_action(sku: SKU, recommended_prep: int, db: Session) -> list[ReplenishmentItem]:
    items: list[ReplenishmentItem] = []
    for bom in db.query(RecipeBOM).filter(RecipeBOM.sku_id == sku.id).all():
        ingredient = db.query(Ingredient).filter(Ingredient.id == bom.ingredient_id).first()
        if not ingredient:
            continue
        required = round(recommended_prep * bom.quantity_per_unit, 3)
        current = round(float(ingredient.stock_on_hand or 0), 3)
        shortage = round(max(0.0, required - current), 3)
        if required <= 0:
            urgency = "low"
        else:
            ratio = current / required
            urgency = "critical" if ratio < 0.5 else "high" if ratio < 0.8 else "medium" if ratio < 1.0 else "low"
        items.append(
            ReplenishmentItem(
                ingredient_id=str(ingredient.id),
                ingredient_name=ingredient.name,
                required_qty=required,
                current_stock=current,
                shortage_qty=shortage,
                reorder_qty=shortage,
                unit=ingredient.unit,
                urgency=urgency,
            )
        )
    return sorted(items, key=lambda item: item.shortage_qty, reverse=True)[:3]


def _optimizer_payload(line: PrepPlanLine) -> dict:
    rationale = line.rationale_json or {}
    payload = rationale.get("optimizer") or rationale.get("decision") or {}
    return payload if isinstance(payload, dict) else {}


def _financial_payload(payload: dict) -> dict:
    financial = payload.get("financial_exposure") or {}
    return financial if isinstance(financial, dict) else {}


def _missing_optimizer_fields(payload: dict) -> list[str]:
    financial = _financial_payload(payload)
    missing = []
    for key in ("batch_size", "waste_cost", "stockout_cost", "reason_summary"):
        if key not in payload:
            missing.append(key)
    for key in ("stockout_exposure_rm", "waste_exposure_rm"):
        if key not in financial:
            missing.append(f"financial_exposure.{key}")
    return missing


def load_recommendation_context(
    recommendation_id: str,
    db: Session,
    manager_adjustment: Optional[ParsedAdjustment] = None,
) -> dict:
    try:
        line_id = int(recommendation_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Recommendation ID must be a prep line ID") from exc

    line = db.query(PrepPlanLine).filter(PrepPlanLine.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if not line.plan:
        raise HTTPException(status_code=422, detail="Recommendation is missing its prep plan")

    forecast_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.forecast_date == line.plan.plan_date)
        .order_by(desc(ForecastRun.created_at), desc(ForecastRun.id))
        .first()
    )
    if not forecast_run:
        raise HTTPException(status_code=422, detail="Forecast run is required for council review")

    forecast_line = next(
        (
            candidate
            for candidate in forecast_run.lines
            if candidate.outlet_id == line.outlet_id and candidate.sku_id == line.sku_id
        ),
        None,
    )
    if not forecast_line:
        raise HTTPException(status_code=422, detail="Forecast line is required for council review")

    outlet = db.query(Outlet).filter(Outlet.id == line.outlet_id).first()
    sku = db.query(SKU).filter(SKU.id == line.sku_id).first()
    if not outlet or not sku:
        raise HTTPException(status_code=422, detail="Outlet and SKU are required for council review")

    if manager_adjustment is not None:
        if (
            manager_adjustment.outlet_id != outlet.name
            or manager_adjustment.daypart.lower() != line.daypart.lower()
            or manager_adjustment.sku_category != sku.category
        ):
            raise HTTPException(
                status_code=422,
                detail="Manager-note adjustment does not match the selected recommendation",
            )

    band = band_for_prep_line(prep_line=line, forecast_line=forecast_line, sku=sku, outlet_code=outlet.code)
    current_prep = line.edited_units if line.edited_units is not None else line.recommended_units
    optimizer = _optimizer_payload(line)
    missing_fields = _missing_optimizer_fields(optimizer)
    evidence_warnings: list[str] = [
        "Using latest forecast run by date because PrepPlan has no direct forecast_run_id link."
    ]
    if missing_fields:
        unit_cost = sku_unit_cost(sku, db)
        fallback_batch_size = int(optimizer.get("batch_size") or 5)
        if "batch_size" in missing_fields:
            evidence_warnings.append("optimizer batch_size missing; fallback batch_size=5 was used")
        decision = calculate_optimal_prep(
            p10=band.p10,
            p50=band.p50,
            p90=band.p90,
            opening_stock=line.current_stock,
            unit_price=float(sku.price or 0),
            unit_cost=unit_cost,
            batch_size=fallback_batch_size,
            capacity=None,
            freshness_hours=sku.freshness_hours,
        )
        evidence_warnings.append(
            "optimizer evidence recalculated because stored rationale_json was incomplete: "
            + ", ".join(missing_fields)
        )
    else:
        decision = optimizer
    replenishment = ingredient_impact_for_action(sku, current_prep, db)
    financial = _financial_payload(decision)

    return {
        "line": line,
        "forecast_run": forecast_run,
        "forecast_line": forecast_line,
        "outlet": outlet,
        "sku": sku,
        "plan_id": line.plan_id,
        "target_date": line.plan.plan_date,
        "recommendation_id": str(line.id),
        "forecast_run_id": forecast_run.forecast_run_id,
        "model_version": forecast_run.model_version,
        "engine_name": forecast_run.engine_name,
        "outlet_id": outlet.id,
        "outlet_name": outlet.name,
        "sku_id": sku.id,
        "sku_name": sku.name,
        "sku_category": sku.category,
        "daypart": line.daypart,
        "p10": float(band.p10),
        "p50": float(band.p50),
        "p90": float(band.p90),
        "opening_stock": float(line.current_stock),
        "current_recommended_prep": int(current_prep),
        "original_recommended_prep": int(line.recommended_units),
        "has_prior_edit": line.edited_units is not None,
        "batch_size": int(decision["batch_size"]),
        "waste_cost": float(decision["waste_cost"]),
        "stockout_cost": float(decision["stockout_cost"]),
        "stockout_exposure_rm": float(financial["stockout_exposure_rm"]),
        "waste_exposure_rm": float(financial["waste_exposure_rm"]),
        "reason_summary": str(decision["reason_summary"]),
        "replenishment": replenishment,
        "inventory_scope": "global_ingredient_stock",
        "evidence_warnings": evidence_warnings,
    }

