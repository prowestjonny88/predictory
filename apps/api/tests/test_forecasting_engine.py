from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base
from db.models import Outlet, SKU, SalesFact, ForecastLine
from forecasting.engine import (
    _weighted_recent_total,
    _weekday_pattern_total,
    _moving_average_14_total,
    forecast_demand,
    run_forecast_for_date,
)


def _build_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def test_forecast_components_math():
    target = date(2026, 1, 8)

    # target-7 .. target-1
    recent_values = [10, 20, 30, 40, 50, 60, 70]
    totals = {target - timedelta(days=7 - i): float(v) for i, v in enumerate(recent_values)}
    weighted = _weighted_recent_total(totals, target)
    assert round(weighted, 2) == round(
        (10 * 0.05) + (20 * 0.05) + (30 * 0.10) + (40 * 0.10) + (50 * 0.15) + (60 * 0.20) + (70 * 0.35),
        2,
    )

    weekday_totals = {
        date(2025, 12, 11): 10.0,  # Thursday
        date(2025, 12, 18): 20.0,  # Thursday
        date(2025, 12, 25): 30.0,  # Thursday
        date(2026, 1, 1): 40.0,    # Thursday
    }
    assert _weekday_pattern_total(weekday_totals, target) == 25.0

    ma_totals = {target - timedelta(days=i): float(i) for i in range(1, 15)}
    assert _moving_average_14_total(ma_totals, target) == 7.5


def test_forecast_uses_daypart_ratios_and_combined_total():
    db = _build_session()
    outlet = Outlet(name="Test Outlet", code="TEST-OUT")
    sku = SKU(
        name="Test Croissant",
        code="TEST-SKU",
        category="Pastry",
        freshness_hours=8,
        is_bestseller=True,
        safety_buffer_pct=0.10,
        price=8.5,
    )
    db.add_all([outlet, sku])
    db.flush()

    target = date(2026, 2, 10)
    start = target - timedelta(days=35)

    # Stable history: total 100/day with 50/30/20 daypart split.
    day = start
    while day < target:
        db.add_all(
            [
                SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=day, daypart="morning", units_sold=50, revenue=425),
                SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=day, daypart="midday", units_sold=30, revenue=255),
                SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=day, daypart="evening", units_sold=20, revenue=170),
            ]
        )
        day += timedelta(days=1)
    db.commit()

    result = forecast_demand(outlet.id, sku.id, target, db)

    assert abs(result.total - 100.0) <= 0.1
    assert abs(result.morning - 50.0) <= 0.1
    assert abs(result.midday - 30.0) <= 0.1
    assert abs(result.evening - 20.0) <= 0.1
    assert result.method == "weighted_blend"


def test_run_forecast_persists_forecast_lines():
    db = _build_session()
    outlets = [
        Outlet(name="Outlet A", code="OUT-A"),
        Outlet(name="Outlet B", code="OUT-B"),
    ]
    skus = [
        SKU(name="SKU A", code="SKU-A", category="Pastry", freshness_hours=8, is_bestseller=False, safety_buffer_pct=0.1, price=8),
        SKU(name="SKU B", code="SKU-B", category="Bread", freshness_hours=24, is_bestseller=False, safety_buffer_pct=0.1, price=12),
    ]
    db.add_all(outlets + skus)
    db.flush()

    target = date(2026, 3, 1)
    for outlet in outlets:
        for sku in skus:
            for i in range(1, 15):
                day = target - timedelta(days=i)
                db.add_all(
                    [
                        SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=day, daypart="morning", units_sold=10, revenue=1),
                        SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=day, daypart="midday", units_sold=8, revenue=1),
                        SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=day, daypart="evening", units_sold=6, revenue=1),
                    ]
                )
    db.commit()

    run = run_forecast_for_date(target, db)
    assert run.id is not None
    assert len(run.lines) == len(outlets) * len(skus)
    assert db.query(ForecastLine).count() == len(outlets) * len(skus)

