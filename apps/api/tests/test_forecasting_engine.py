from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from db.models import (
    AuditEvent,
    ForecastLine,
    ForecastOverride,
    HolidayCalendar,
    InventorySnapshot,
    Outlet,
    SKU,
    SalesFact,
    WeatherSnapshot,
)
from forecasting.engine import (
    _weighted_recent_total,
    _weekday_pattern_total,
    _moving_average_14_total,
    _blend_total_with_available_signals,
    forecast_demand,
    run_forecast_for_date,
)
from main import app


def _build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def _build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


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


def test_blend_renormalizes_when_weekday_signal_missing():
    combined, applied = _blend_total_with_available_signals(
        weighted_total=100.0,
        weekday_total=0.0,
        ma14_total=100.0,
        has_recent=True,
        has_weekday=False,
        has_ma14=True,
    )
    # Base 0.4 + 0.2 gets renormalized to 2/3 and 1/3.
    assert round(applied["weighted_recent_total"], 3) == 0.667
    assert applied["weekday_pattern_total"] == 0.0
    assert round(applied["moving_avg_14d_total"], 3) == 0.333
    assert abs(combined - 100.0) <= 0.1


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


def test_adjust_forecast_line_rejects_below_negative_100_percent():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    outlet = Outlet(name="Outlet A", code="OUT-A")
    sku = SKU(name="SKU A", code="SKU-A", category="Pastry", freshness_hours=8, is_bestseller=False, safety_buffer_pct=0.1, price=8)
    db.add_all([outlet, sku])
    db.flush()

    target = date(2026, 3, 1)
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
    line = run.lines[0]
    db.close()

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            resp = client.patch(
                f"/api/v1/forecasts/{run.id}/lines/{line.id}",
                json={"manual_adjustment_pct": -101},
            )
            assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_adjust_forecast_line_persists_audit_event():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    outlet = Outlet(name="Outlet A", code="OUT-A")
    sku = SKU(name="SKU A", code="SKU-A", category="Pastry", freshness_hours=8, is_bestseller=False, safety_buffer_pct=0.1, price=8)
    db.add_all([outlet, sku])
    db.flush()

    target = date(2026, 3, 1)
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
    line = run.lines[0]
    before_total = line.total
    db.close()

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            resp = client.patch(
                f"/api/v1/forecasts/{run.id}/lines/{line.id}",
                json={"manual_adjustment_pct": 10, "user_id": "planner"},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["manual_adjustment_pct"] == 10
            assert payload["total"] > before_total

        db = SessionLocal()
        audit = db.query(AuditEvent).filter(AuditEvent.entity_id == line.id).one()
        assert audit.event_type == "forecast_line_adjusted"
        assert audit.entity_type == "ForecastLine"
        assert audit.user_id == "planner"
        assert audit.before_value["manual_adjustment_pct"] is None
        assert audit.after_value["manual_adjustment_pct"] == 10
        assert audit.after_value["total"] > audit.before_value["total"]
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_forecast_holiday_flag_without_uplift_does_not_change_total_but_is_recorded():
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

    target = date(2026, 4, 10)
    db.add(
        HolidayCalendar(
            holiday_date=target,
            name="Demo Public Holiday",
            country_code="MY",
            holiday_type="Public holiday",
            demand_uplift_pct=0.0,
            source="test",
        )
    )

    start = target - timedelta(days=35)
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
    assert result.rationale["holiday_signal"]["label"] == "Demo Public Holiday"
    assert result.rationale["holiday_signal"]["adjustment_pct"] == 0.0
    assert result.rationale["context_adjustment_pct"] == 0.0


def test_forecast_applies_live_weather_snapshot_adjustment():
    db = _build_session()
    outlet = Outlet(name="Test Outlet", code="TEST-OUT", latitude=3.1, longitude=101.6)
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

    target = date(2026, 4, 10)
    db.add(
        WeatherSnapshot(
            outlet_id=outlet.id,
            target_date=target,
            summary="Light rain",
            rain_mm=3.4,
            temp_max_c=31.2,
            adjustment_pct=-2.0,
            status="applied",
            source="live",
            raw_json={"test": True},
        )
    )

    start = target - timedelta(days=35)
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

    assert round(result.total, 1) == 98.0
    assert result.rationale["weather_signal"]["label"] == "Light rain"
    assert result.rationale["weather_signal"]["adjustment_pct"] == -2.0
    assert result.rationale["context_adjustment_pct"] == -2.0


def test_forecast_manual_override_and_stockout_censoring_are_recorded():
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

    target = date(2026, 4, 10)
    db.add(
        ForecastOverride(
            target_date=target,
            outlet_id=outlet.id,
            sku_id=sku.id,
            override_type="promo",
            title="Instagram push",
            adjustment_pct=10.0,
            enabled=True,
            created_by="tester",
        )
    )

    for i in range(1, 36):
        day = target - timedelta(days=i)
        db.add_all(
            [
                SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=day, daypart="morning", units_sold=50, revenue=425),
                SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=day, daypart="midday", units_sold=30, revenue=255),
                SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=day, daypart="evening", units_sold=20, revenue=170),
            ]
        )
        eod_stock = 0 if i in (3, 9) else 6
        db.add(
            InventorySnapshot(
                outlet_id=outlet.id,
                sku_id=sku.id,
                snapshot_date=day,
                snapshot_time="eod",
                units_on_hand=eod_stock,
            )
        )
    db.commit()

    result = forecast_demand(outlet.id, sku.id, target, db)

    assert result.total > 110.0
    assert result.rationale["manual_overrides"][0]["title"] == "Instagram push"
    assert result.rationale["stockout_censoring"]["adjusted_history_days"] >= 1
    assert result.rationale["context_adjustment_pct"] == 10.0
