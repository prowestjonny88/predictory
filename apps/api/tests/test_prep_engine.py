from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base
from db.models import Outlet, SKU, InventorySnapshot, SalesFact, WasteLog
from forecasting.engine import ForecastResult
from planning.prep import recommend_prep


def _build_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def _seed_outlet_sku(db, sku_code: str, freshness_hours: int, safety_buffer_pct: float):
    outlet = Outlet(name="Test Outlet", code=f"OUT-{sku_code}")
    sku = SKU(
        name=f"SKU {sku_code}",
        code=sku_code,
        category="Pastry",
        freshness_hours=freshness_hours,
        is_bestseller=False,
        safety_buffer_pct=safety_buffer_pct,
        price=10.0,
    )
    db.add_all([outlet, sku])
    db.flush()
    return outlet, sku


def test_recommend_prep_zero_stock_uses_formula():
    db = _build_session()
    outlet, sku = _seed_outlet_sku(db, "SKU-ZERO", freshness_hours=12, safety_buffer_pct=0.10)
    target = date(2026, 3, 5)

    forecast = ForecastResult(
        outlet_id=outlet.id,
        sku_id=sku.id,
        target_date=target,
        morning=10,
        midday=10,
        evening=10,
        total=30,
    )
    rec = recommend_prep(outlet.id, sku.id, target, db, forecast=forecast)

    assert rec.morning == 11
    assert rec.midday == 11
    assert rec.evening == 11


def test_recommend_prep_full_stock_zeroes_prep():
    db = _build_session()
    outlet, sku = _seed_outlet_sku(db, "SKU-FULL", freshness_hours=12, safety_buffer_pct=0.10)
    target = date(2026, 3, 5)

    db.add(
        InventorySnapshot(
            outlet_id=outlet.id,
            sku_id=sku.id,
            snapshot_date=target - timedelta(days=1),
            snapshot_time="eod",
            units_on_hand=100,
        )
    )
    db.commit()

    forecast = ForecastResult(
        outlet_id=outlet.id,
        sku_id=sku.id,
        target_date=target,
        morning=10,
        midday=10,
        evening=10,
        total=30,
    )
    rec = recommend_prep(outlet.id, sku.id, target, db, forecast=forecast)

    assert rec.morning == 0
    assert rec.midday == 0
    assert rec.evening == 0


def test_short_freshness_skips_evening_when_morning_prep_exists():
    db = _build_session()
    outlet, sku = _seed_outlet_sku(db, "SKU-SHORT", freshness_hours=6, safety_buffer_pct=0.10)
    target = date(2026, 3, 5)

    forecast = ForecastResult(
        outlet_id=outlet.id,
        sku_id=sku.id,
        target_date=target,
        morning=10,
        midday=5,
        evening=8,
        total=23,
    )
    rec = recommend_prep(outlet.id, sku.id, target, db, forecast=forecast)

    assert rec.morning > 0
    assert rec.evening == 0


def test_high_waste_history_reduces_prep_by_5pct():
    db = _build_session()
    outlet, sku = _seed_outlet_sku(db, "SKU-WASTE", freshness_hours=12, safety_buffer_pct=0.0)
    target = date(2026, 3, 10)

    # Waste rate over 7 days > 15%
    for i in range(1, 8):
        day = target - timedelta(days=i)
        db.add(SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=day, daypart="morning", units_sold=10, revenue=0))
        db.add(WasteLog(outlet_id=outlet.id, sku_id=sku.id, waste_date=day, daypart="evening", units_wasted=3, reason="test"))
    db.commit()

    forecast = ForecastResult(
        outlet_id=outlet.id,
        sku_id=sku.id,
        target_date=target,
        morning=20,
        midday=0,
        evening=0,
        total=20,
    )
    rec = recommend_prep(outlet.id, sku.id, target, db, forecast=forecast)

    # 20 reduced by 5% = 19
    assert rec.morning == 19

