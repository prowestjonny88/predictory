"""Add forecast context tables and outlet coordinates

Revision ID: 002
Revises: 001
Create Date: 2026-03-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("outlets", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("outlets", sa.Column("longitude", sa.Float(), nullable=True))

    op.create_table(
        "holiday_calendar",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country_code", sa.String(10), server_default="MY", nullable=False),
        sa.Column("region_code", sa.String(50), nullable=True),
        sa.Column("holiday_type", sa.String(100), nullable=True),
        sa.Column("demand_uplift_pct", sa.Float(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("source", sa.String(50), server_default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_holiday_calendar_holiday_date", "holiday_calendar", ["holiday_date"])

    op.create_table(
        "weather_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.id"), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.String(255), server_default="Unavailable", nullable=False),
        sa.Column("rain_mm", sa.Float(), nullable=True),
        sa.Column("temp_max_c", sa.Float(), nullable=True),
        sa.Column("adjustment_pct", sa.Float(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="unavailable", nullable=False),
        sa.Column("source", sa.String(50), server_default="fallback", nullable=False),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("outlet_id", "target_date", name="uq_weather_snapshot_outlet_date"),
    )
    op.create_index("ix_weather_snapshots_target_date", "weather_snapshots", ["target_date"])

    op.create_table(
        "forecast_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.id"), nullable=False),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=True),
        sa.Column("override_type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("adjustment_pct", sa.Float(), server_default="0", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_forecast_overrides_target_date", "forecast_overrides", ["target_date"])


def downgrade() -> None:
    op.drop_index("ix_forecast_overrides_target_date", table_name="forecast_overrides")
    op.drop_table("forecast_overrides")

    op.drop_index("ix_weather_snapshots_target_date", table_name="weather_snapshots")
    op.drop_table("weather_snapshots")

    op.drop_index("ix_holiday_calendar_holiday_date", table_name="holiday_calendar")
    op.drop_table("holiday_calendar")

    op.drop_column("outlets", "longitude")
    op.drop_column("outlets", "latitude")
