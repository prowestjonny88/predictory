"""
Catalog router — Task 4
GET /outlets, /skus, /ingredients, /recipes, /sales, /inventory, /wastelogs
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import Outlet, SKU, Ingredient, RecipeBOM, SalesFact, InventorySnapshot, WasteLog

router = APIRouter()


# ─── Pydantic response schemas ────────────────────────────────────────────────

class OutletOut(BaseModel):
    id: int
    name: str
    code: str
    address: Optional[str]
    is_active: bool
    model_config = {"from_attributes": True}

class SKUOut(BaseModel):
    id: int
    name: str
    code: str
    category: str
    freshness_hours: int
    is_bestseller: bool
    safety_buffer_pct: float
    price: float
    is_active: bool
    model_config = {"from_attributes": True}

class IngredientOut(BaseModel):
    id: int
    name: str
    code: str
    unit: str
    stock_on_hand: float
    reorder_point: float
    supplier_lead_time_hours: int
    cost_per_unit: float
    model_config = {"from_attributes": True}

class RecipeOut(BaseModel):
    id: int
    sku_id: int
    sku_name: str
    ingredient_id: int
    ingredient_name: str
    quantity_per_unit: float
    unit: str
    model_config = {"from_attributes": True}

class SalesFactOut(BaseModel):
    id: int
    outlet_id: int
    sku_id: int
    sale_date: date
    daypart: str
    units_sold: int
    revenue: float
    model_config = {"from_attributes": True}

class InventoryOut(BaseModel):
    id: int
    outlet_id: int
    sku_id: int
    sku_name: str
    snapshot_date: date
    snapshot_time: str
    units_on_hand: int
    model_config = {"from_attributes": True}

class WasteLogOut(BaseModel):
    id: int
    outlet_id: int
    sku_id: int
    waste_date: date
    daypart: str
    units_wasted: int
    reason: Optional[str]
    model_config = {"from_attributes": True}


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/outlets", response_model=list[OutletOut])
def get_outlets(db: Session = Depends(get_db)):
    return db.query(Outlet).filter(Outlet.is_active == True).all()


@router.get("/skus", response_model=list[SKUOut])
def get_skus(db: Session = Depends(get_db)):
    return db.query(SKU).filter(SKU.is_active == True).all()


@router.get("/ingredients", response_model=list[IngredientOut])
def get_ingredients(db: Session = Depends(get_db)):
    return db.query(Ingredient).filter(Ingredient.is_active == True).all()


@router.get("/recipes", response_model=list[RecipeOut])
def get_recipes(db: Session = Depends(get_db)):
    rows = db.query(RecipeBOM).join(RecipeBOM.sku).join(RecipeBOM.ingredient).all()
    return [
        RecipeOut(
            id=r.id,
            sku_id=r.sku_id,
            sku_name=r.sku.name,
            ingredient_id=r.ingredient_id,
            ingredient_name=r.ingredient.name,
            quantity_per_unit=r.quantity_per_unit,
            unit=r.unit,
        )
        for r in rows
    ]


@router.get("/sales", response_model=list[SalesFactOut])
def get_sales(
    outlet_id: Optional[int] = Query(None),
    sku_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(SalesFact)
    if outlet_id:
        q = q.filter(SalesFact.outlet_id == outlet_id)
    if sku_id:
        q = q.filter(SalesFact.sku_id == sku_id)
    if start_date:
        q = q.filter(SalesFact.sale_date >= start_date)
    if end_date:
        q = q.filter(SalesFact.sale_date <= end_date)
    return q.order_by(SalesFact.sale_date.desc()).offset(offset).limit(limit).all()


@router.get("/inventory", response_model=list[InventoryOut])
def get_inventory(
    outlet_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(InventorySnapshot).join(InventorySnapshot.sku)
    if outlet_id:
        q = q.filter(InventorySnapshot.outlet_id == outlet_id)
    rows = q.order_by(InventorySnapshot.snapshot_date.desc()).limit(200).all()
    return [
        InventoryOut(
            id=r.id,
            outlet_id=r.outlet_id,
            sku_id=r.sku_id,
            sku_name=r.sku.name,
            snapshot_date=r.snapshot_date,
            snapshot_time=r.snapshot_time,
            units_on_hand=r.units_on_hand,
        )
        for r in rows
    ]


@router.get("/wastelogs", response_model=list[WasteLogOut])
def get_waste_logs(
    outlet_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(WasteLog)
    if outlet_id:
        q = q.filter(WasteLog.outlet_id == outlet_id)
    if start_date:
        q = q.filter(WasteLog.waste_date >= start_date)
    if end_date:
        q = q.filter(WasteLog.waste_date <= end_date)
    return q.order_by(WasteLog.waste_date.desc()).limit(500).all()
