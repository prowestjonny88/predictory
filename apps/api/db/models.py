from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from db.database import Base


# ─── Master Data ─────────────────────────────────────────────────────────────

class Outlet(Base):
    __tablename__ = "outlets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sales_facts = relationship("SalesFact", back_populates="outlet")
    inventory_snapshots = relationship("InventorySnapshot", back_populates="outlet")
    waste_logs = relationship("WasteLog", back_populates="outlet")


class SKU(Base):
    __tablename__ = "skus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    freshness_hours: Mapped[int] = mapped_column(Integer, default=8)
    is_bestseller: Mapped[bool] = mapped_column(Boolean, default=False)
    safety_buffer_pct: Mapped[float] = mapped_column(Float, default=0.10)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe_bom = relationship("RecipeBOM", back_populates="sku")
    sales_facts = relationship("SalesFact", back_populates="sku")
    inventory_snapshots = relationship("InventorySnapshot", back_populates="sku")
    waste_logs = relationship("WasteLog", back_populates="sku")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_on_hand: Mapped[float] = mapped_column(Float, default=0.0)
    reorder_point: Mapped[float] = mapped_column(Float, default=0.0)
    supplier_lead_time_hours: Mapped[int] = mapped_column(Integer, default=24)
    cost_per_unit: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe_bom = relationship("RecipeBOM", back_populates="ingredient")


class RecipeBOM(Base):
    __tablename__ = "recipe_bom"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("skus.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    sku = relationship("SKU", back_populates="recipe_bom")
    ingredient = relationship("Ingredient", back_populates="recipe_bom")

    __table_args__ = (UniqueConstraint("sku_id", "ingredient_id", name="uq_sku_ingredient"),)


# ─── Operational Data ────────────────────────────────────────────────────────

class SalesFact(Base):
    __tablename__ = "sales_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    outlet_id: Mapped[int] = mapped_column(Integer, ForeignKey("outlets.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("skus.id"), nullable=False)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    daypart: Mapped[str] = mapped_column(String(20), nullable=False)  # morning/midday/evening
    units_sold: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    outlet = relationship("Outlet", back_populates="sales_facts")
    sku = relationship("SKU", back_populates="sales_facts")

    __table_args__ = (
        UniqueConstraint("outlet_id", "sku_id", "sale_date", "daypart", name="uq_sales_fact"),
    )


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    outlet_id: Mapped[int] = mapped_column(Integer, ForeignKey("outlets.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("skus.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    snapshot_time: Mapped[str] = mapped_column(String(20), nullable=False)  # morning/midday/evening/eod
    units_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    outlet = relationship("Outlet", back_populates="inventory_snapshots")
    sku = relationship("SKU", back_populates="inventory_snapshots")


class WasteLog(Base):
    __tablename__ = "waste_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    outlet_id: Mapped[int] = mapped_column(Integer, ForeignKey("outlets.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("skus.id"), nullable=False)
    waste_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    daypart: Mapped[str] = mapped_column(String(20), nullable=False)
    units_wasted: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    outlet = relationship("Outlet", back_populates="waste_logs")
    sku = relationship("SKU", back_populates="waste_logs")


# ─── Forecasting ─────────────────────────────────────────────────────────────

class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines = relationship("ForecastLine", back_populates="run", cascade="all, delete-orphan")


class ForecastLine(Base):
    __tablename__ = "forecast_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("forecast_runs.id"), nullable=False)
    outlet_id: Mapped[int] = mapped_column(Integer, ForeignKey("outlets.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("skus.id"), nullable=False)
    morning: Mapped[float] = mapped_column(Float, default=0.0)
    midday: Mapped[float] = mapped_column(Float, default=0.0)
    evening: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    method: Mapped[str] = mapped_column(String(50), default="weighted_blend")
    confidence: Mapped[float] = mapped_column(Float, default=0.80)
    manual_adjustment_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rationale_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    run = relationship("ForecastRun", back_populates="lines")


# ─── Planning ─────────────────────────────────────────────────────────────────

class PrepPlan(Base):
    __tablename__ = "prep_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/approved
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines = relationship("PrepPlanLine", back_populates="plan", cascade="all, delete-orphan")


class PrepPlanLine(Base):
    __tablename__ = "prep_plan_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("prep_plans.id"), nullable=False)
    outlet_id: Mapped[int] = mapped_column(Integer, ForeignKey("outlets.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("skus.id"), nullable=False)
    daypart: Mapped[str] = mapped_column(String(20), nullable=False)
    recommended_units: Mapped[int] = mapped_column(Integer, default=0)
    edited_units: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_stock: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/accepted/edited
    rationale_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    plan = relationship("PrepPlan", back_populates="lines")


class ReplenishmentPlan(Base):
    __tablename__ = "replenishment_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines = relationship("ReplenishmentPlanLine", back_populates="plan", cascade="all, delete-orphan")


class ReplenishmentPlanLine(Base):
    __tablename__ = "replenishment_plan_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("replenishment_plans.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id"), nullable=False)
    need_qty: Mapped[float] = mapped_column(Float, default=0.0)
    stock_on_hand: Mapped[float] = mapped_column(Float, default=0.0)
    reorder_qty: Mapped[float] = mapped_column(Float, default=0.0)
    urgency: Mapped[str] = mapped_column(String(20), default="low")  # critical/high/medium/low
    driving_skus: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    rationale_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_ordered: Mapped[bool] = mapped_column(Boolean, default=False)

    plan = relationship("ReplenishmentPlan", back_populates="lines")
    ingredient = relationship("Ingredient")


# ─── Audit ────────────────────────────────────────────────────────────────────

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    before_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
