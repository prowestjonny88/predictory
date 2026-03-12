from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from db.models import ForecastOverride, HolidayCalendar, InventorySnapshot, Outlet, SKU, SalesFact, WeatherSnapshot
from main import app


def _build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _override_app_db(SessionLocal):
    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db


def test_forecast_context_returns_expected_schema_and_combined_adjustment():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    outlet = Outlet(name="Test Outlet", code="OUT-A", latitude=3.1, longitude=101.6)
    sku = SKU(name="Butter Croissant", code="SKU-A", category="Pastry", freshness_hours=8, is_bestseller=True, safety_buffer_pct=0.1, price=8.0)
    db.add_all([outlet, sku])
    db.flush()

    target_date = date(2026, 4, 10)
    db.add(
        HolidayCalendar(
            holiday_date=target_date,
            name="Demo Festival Day",
            country_code="MY",
            holiday_type="Festival",
            demand_uplift_pct=5.0,
            source="test",
        )
    )
    db.add(
        WeatherSnapshot(
            outlet_id=outlet.id,
            target_date=target_date,
            summary="Light rain",
            rain_mm=3.4,
            temp_max_c=31.2,
            adjustment_pct=-2.0,
            status="applied",
            source="live",
            raw_json={"test": True},
        )
    )
    db.add(
        ForecastOverride(
            target_date=target_date,
            outlet_id=outlet.id,
            sku_id=sku.id,
            override_type="promo",
            title="Morning push",
            adjustment_pct=10.0,
            enabled=True,
            created_by="tester",
        )
    )
    for i in range(1, 10):
        sales_day = target_date - timedelta(days=i)
        db.add_all(
            [
                SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=sales_day, daypart="morning", units_sold=40, revenue=1),
                SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=sales_day, daypart="midday", units_sold=30, revenue=1),
                SalesFact(outlet_id=outlet.id, sku_id=sku.id, sale_date=sales_day, daypart="evening", units_sold=20, revenue=1),
                InventorySnapshot(
                    outlet_id=outlet.id,
                    sku_id=sku.id,
                    snapshot_date=sales_day,
                    snapshot_time="eod",
                    units_on_hand=0 if i == 3 else 6,
                ),
            ]
        )
    db.commit()
    outlet_id = outlet.id
    sku_id = sku.id
    db.close()

    _override_app_db(SessionLocal)
    try:
        with TestClient(app) as client:
            resp = client.get(
                "/api/v1/forecast-context",
                params={
                    "target_date": target_date.isoformat(),
                    "outlet_id": outlet_id,
                    "sku_id": sku_id,
                },
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["holiday"]["label"] == "Demo Festival Day"
            assert payload["weather"]["label"] == "Light rain"
            assert payload["stockout_censoring"]["adjusted_history_days"] >= 1
            assert len(payload["active_overrides"]) == 1
            assert payload["combined_adjustment_pct"] == 13.0
    finally:
        app.dependency_overrides.clear()


def test_forecast_override_crud_lifecycle():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    outlet = Outlet(name="Test Outlet", code="OUT-A")
    sku = SKU(name="Butter Croissant", code="SKU-A", category="Pastry", freshness_hours=8, is_bestseller=True, safety_buffer_pct=0.1, price=8.0)
    db.add_all([outlet, sku])
    db.commit()
    db.refresh(outlet)
    db.refresh(sku)
    outlet_id = outlet.id
    sku_id = sku.id
    db.close()

    _override_app_db(SessionLocal)
    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/api/v1/forecast-overrides",
                json={
                    "target_date": date(2026, 4, 10).isoformat(),
                    "outlet_id": outlet_id,
                    "sku_id": sku_id,
                    "override_type": "promo",
                    "title": "Morning push",
                    "notes": "Instagram",
                    "adjustment_pct": 12.0,
                    "enabled": True,
                    "created_by": "planner",
                },
            )
            assert create_resp.status_code == 200
            override_id = create_resp.json()["id"]

            list_resp = client.get(
                "/api/v1/forecast-overrides",
                params={
                    "target_date": date(2026, 4, 10).isoformat(),
                    "outlet_id": outlet_id,
                    "sku_id": sku_id,
                },
            )
            assert list_resp.status_code == 200
            assert len(list_resp.json()) == 1

            update_resp = client.patch(
                f"/api/v1/forecast-overrides/{override_id}",
                json={"adjustment_pct": 8.0, "enabled": False},
            )
            assert update_resp.status_code == 200
            assert update_resp.json()["adjustment_pct"] == 8.0
            assert update_resp.json()["enabled"] is False

            delete_resp = client.delete(f"/api/v1/forecast-overrides/{override_id}")
            assert delete_resp.status_code == 204

            list_after_delete = client.get(
                "/api/v1/forecast-overrides",
                params={
                    "target_date": date(2026, 4, 10).isoformat(),
                    "outlet_id": outlet.id,
                    "sku_id": sku.id,
                },
            )
            assert list_after_delete.status_code == 200
            assert list_after_delete.json() == []
    finally:
        app.dependency_overrides.clear()


def test_forecast_context_returns_weather_fallback_when_snapshot_unavailable():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    outlet = Outlet(name="Test Outlet", code="OUT-A")
    sku = SKU(name="Butter Croissant", code="SKU-A", category="Pastry", freshness_hours=8, is_bestseller=True, safety_buffer_pct=0.1, price=8.0)
    db.add_all([outlet, sku])
    db.commit()
    db.refresh(outlet)
    db.refresh(sku)
    outlet_id = outlet.id
    sku_id = sku.id
    db.close()

    _override_app_db(SessionLocal)
    try:
        with TestClient(app) as client:
            resp = client.get(
                "/api/v1/forecast-context",
                params={
                    "target_date": date(2026, 4, 10).isoformat(),
                    "outlet_id": outlet_id,
                    "sku_id": sku_id,
                },
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["weather"]["source"] == "fallback"
            assert payload["weather"]["adjustment_pct"] == 0.0
            assert payload["weather"]["status"] == "unavailable"
    finally:
        app.dependency_overrides.clear()
