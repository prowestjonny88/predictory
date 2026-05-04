"""Align backend contract tables with API models

Revision ID: 003
Revises: 002
Create Date: 2026-05-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "model_runs" not in tables:
        op.create_table(
            "model_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("model_version", sa.String(100), nullable=False),
            sa.Column("engine_name", sa.String(100), nullable=False),
            sa.Column("status", sa.String(20), server_default="completed", nullable=False),
            sa.Column("metrics", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    forecast_columns = {column["name"] for column in inspector.get_columns("forecast_runs")}
    with op.batch_alter_table("forecast_runs") as batch_op:
        if "forecast_run_id" not in forecast_columns:
            batch_op.add_column(sa.Column("forecast_run_id", sa.String(50), nullable=True))
        if "model_run_id" not in forecast_columns:
            batch_op.add_column(sa.Column("model_run_id", sa.Integer(), nullable=True))
        if "engine_name" not in forecast_columns:
            batch_op.add_column(sa.Column("engine_name", sa.String(100), server_default="baseline_heuristic", nullable=False))
        if "model_version" not in forecast_columns:
            batch_op.add_column(sa.Column("model_version", sa.String(100), server_default="unknown", nullable=False))

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "prep_recommendations" not in tables:
        op.create_table(
            "prep_recommendations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("forecast_run_id", sa.String(50), nullable=False),
            sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.id"), nullable=False),
            sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
            sa.Column("daypart", sa.String(20), nullable=False),
            sa.Column("p10", sa.Float(), nullable=False),
            sa.Column("p50", sa.Float(), nullable=False),
            sa.Column("p90", sa.Float(), nullable=False),
            sa.Column("opening_stock", sa.Integer(), server_default="0", nullable=False),
            sa.Column("recommended_prep", sa.Integer(), nullable=False),
            sa.Column("batch_size", sa.Integer(), server_default="5", nullable=False),
            sa.Column("waste_cost", sa.Float(), nullable=False),
            sa.Column("stockout_cost", sa.Float(), nullable=False),
            sa.Column("financial_exposure", sa.JSON(), nullable=False),
            sa.Column("reason_summary", sa.Text(), nullable=False),
            sa.Column("status", sa.String(20), server_default="pending_approval", nullable=False),
            sa.Column("final_prep", sa.Integer(), nullable=True),
            sa.Column("operator_action", sa.String(50), nullable=True),
            sa.Column("operator_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "replenishment_recommendations" not in tables:
        op.create_table(
            "replenishment_recommendations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("forecast_run_id", sa.String(50), nullable=False),
            sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id"), nullable=False),
            sa.Column("required_qty", sa.Float(), nullable=False),
            sa.Column("current_stock", sa.Float(), nullable=False),
            sa.Column("shortage_qty", sa.Float(), nullable=False),
            sa.Column("reorder_qty", sa.Float(), nullable=False),
            sa.Column("unit", sa.String(20), nullable=False),
            sa.Column("urgency", sa.String(20), nullable=False),
            sa.Column("driving_skus", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(20), server_default="pending", nullable=False),
            sa.Column("is_ordered", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "decision_audit_events" not in tables:
        op.create_table(
            "decision_audit_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("forecast_run_id", sa.String(50), nullable=False),
            sa.Column("model_version", sa.String(100), nullable=False),
            sa.Column("engine_name", sa.String(100), nullable=False),
            sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.id"), nullable=False),
            sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
            sa.Column("daypart", sa.String(20), nullable=False),
            sa.Column("p10", sa.Float(), nullable=False),
            sa.Column("p50", sa.Float(), nullable=False),
            sa.Column("p90", sa.Float(), nullable=False),
            sa.Column("recommended_prep", sa.Integer(), nullable=False),
            sa.Column("final_prep", sa.Integer(), nullable=False),
            sa.Column("operator_action", sa.String(50), nullable=False),
            sa.Column("operator_reason", sa.Text(), nullable=False),
            sa.Column("gemini_note_adjustment_applied", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("gemini_note_summary", sa.Text(), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("decision_audit_events")
    op.drop_table("replenishment_recommendations")
    op.drop_table("prep_recommendations")
    with op.batch_alter_table("forecast_runs") as batch_op:
        batch_op.drop_constraint("uq_forecast_runs_forecast_run_id", type_="unique")
        batch_op.drop_constraint("fk_forecast_runs_model_run_id", type_="foreignkey")
        batch_op.drop_column("model_version")
        batch_op.drop_column("engine_name")
        batch_op.drop_column("model_run_id")
        batch_op.drop_column("forecast_run_id")
    op.drop_table("model_runs")
