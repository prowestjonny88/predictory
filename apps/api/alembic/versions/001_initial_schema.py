"""Initial schema — all BakeWise core tables

Revision ID: 001
Revises:
Create Date: 2026-03-11
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outlets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "skus",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("freshness_hours", sa.Integer(), server_default="8"),
        sa.Column("is_bestseller", sa.Boolean(), server_default="false"),
        sa.Column("safety_buffer_pct", sa.Float(), server_default="0.10"),
        sa.Column("price", sa.Float(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("stock_on_hand", sa.Float(), server_default="0"),
        sa.Column("reorder_point", sa.Float(), server_default="0"),
        sa.Column("supplier_lead_time_hours", sa.Integer(), server_default="24"),
        sa.Column("cost_per_unit", sa.Float(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "recipe_bom",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id"), nullable=False),
        sa.Column("quantity_per_unit", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.UniqueConstraint("sku_id", "ingredient_id", name="uq_sku_ingredient"),
    )
    op.create_table(
        "sales_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.id"), nullable=False),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=False, index=True),
        sa.Column("daypart", sa.String(20), nullable=False),
        sa.Column("units_sold", sa.Integer(), server_default="0"),
        sa.Column("revenue", sa.Float(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("outlet_id", "sku_id", "sale_date", "daypart", name="uq_sales_fact"),
    )
    op.create_table(
        "inventory_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.id"), nullable=False),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False, index=True),
        sa.Column("snapshot_time", sa.String(20), nullable=False),
        sa.Column("units_on_hand", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "waste_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.id"), nullable=False),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
        sa.Column("waste_date", sa.Date(), nullable=False, index=True),
        sa.Column("daypart", sa.String(20), nullable=False),
        sa.Column("units_wasted", sa.Integer(), server_default="0"),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "forecast_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("forecast_date", sa.Date(), nullable=False, index=True),
        sa.Column("status", sa.String(20), server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "forecast_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("forecast_runs.id"), nullable=False),
        sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.id"), nullable=False),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
        sa.Column("morning", sa.Float(), server_default="0"),
        sa.Column("midday", sa.Float(), server_default="0"),
        sa.Column("evening", sa.Float(), server_default="0"),
        sa.Column("total", sa.Float(), server_default="0"),
        sa.Column("method", sa.String(50), server_default="weighted_blend"),
        sa.Column("confidence", sa.Float(), server_default="0.80"),
        sa.Column("manual_adjustment_pct", sa.Float(), nullable=True),
        sa.Column("rationale_json", sa.JSON(), nullable=True),
    )
    op.create_table(
        "prep_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_date", sa.Date(), nullable=False, index=True),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "prep_plan_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("prep_plans.id"), nullable=False),
        sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.id"), nullable=False),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
        sa.Column("daypart", sa.String(20), nullable=False),
        sa.Column("recommended_units", sa.Integer(), server_default="0"),
        sa.Column("edited_units", sa.Integer(), nullable=True),
        sa.Column("current_stock", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("rationale_json", sa.JSON(), nullable=True),
    )
    op.create_table(
        "replenishment_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_date", sa.Date(), nullable=False, index=True),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "replenishment_plan_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("replenishment_plans.id"), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id"), nullable=False),
        sa.Column("need_qty", sa.Float(), server_default="0"),
        sa.Column("stock_on_hand", sa.Float(), server_default="0"),
        sa.Column("reorder_qty", sa.Float(), server_default="0"),
        sa.Column("urgency", sa.String(20), server_default="low"),
        sa.Column("driving_skus", sa.JSON(), nullable=True),
        sa.Column("rationale_json", sa.JSON(), nullable=True),
        sa.Column("is_ordered", sa.Boolean(), server_default="false"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("before_value", sa.JSON(), nullable=True),
        sa.Column("after_value", sa.JSON(), nullable=True),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in [
        "audit_events", "replenishment_plan_lines", "replenishment_plans",
        "prep_plan_lines", "prep_plans", "forecast_lines", "forecast_runs",
        "waste_logs", "inventory_snapshots", "sales_facts",
        "recipe_bom", "ingredients", "skus", "outlets",
    ]:
        op.drop_table(table)
