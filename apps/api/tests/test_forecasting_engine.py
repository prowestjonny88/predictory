from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from db.models import AuditEvent, ForecastLine, Outlet, SKU, WeatherSnapshot
from factories import load_test_dataset
from forecasting.engine import forecast_demand, run_forecast_for_date
from main import app
from services import runtime_readiness
from services.lightgbm_inference import ENGINE_NAME, MODEL_METHOD
from services.runtime_readiness import ReadinessError, check_runtime_readiness


def _build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def test_empty_db_readiness_reports_blocking_errors():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    status = check_runtime_readiness(date.today(), db)
    db.close()

    assert status.ready is False
    assert any("No active outlets" in item for item in status.blockers)
    assert any("No active SKUs" in item for item in status.blockers)
    assert any("No historical sales" in item for item in status.blockers)


def test_readiness_refreshes_missing_weather_before_blocking(monkeypatch):
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    load_test_dataset(db, target_date=target)
    db.query(WeatherSnapshot).filter(WeatherSnapshot.target_date == target).delete()
    db.commit()

    def fake_refresh(outlet, target_date, session):
        snapshot = WeatherSnapshot(
            outlet_id=outlet.id,
            target_date=target_date,
            summary="Stable weather",
            rain_mm=0.0,
            temp_max_c=29.5,
            adjustment_pct=0.0,
            status="neutral",
            source="test_refresh",
            raw_json={"source": "test_refresh"},
        )
        session.add(snapshot)
        session.commit()
        return snapshot

    monkeypatch.setattr(runtime_readiness, "get_or_refresh_weather_snapshot", fake_refresh)

    status = check_runtime_readiness(target, db)
    db.close()

    assert status.ready is True
    assert "weather_coverage" not in status.grouped_blockers


def test_forecast_demand_uses_lightgbm_artifacts_and_residual_bands():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    load_test_dataset(db, target_date=target)
    outlet = db.query(Outlet).filter(Outlet.code == "klcc_mall").one()
    sku = db.query(SKU).filter(SKU.code == "butter_croissant").one()

    result = forecast_demand(outlet.id, sku.id, target, db)
    db.close()

    assert result.method == MODEL_METHOD
    assert result.total > 0
    assert result.rationale["engine_name"] == ENGINE_NAME
    assert result.rationale["feature_rows"]["morning"]["encoded_feature_count"] > 0
    morning_band = result.rationale["uncertainty"]["morning"]
    assert morning_band["p10"] <= morning_band["p50"] <= morning_band["p90"]
    assert "source" in morning_band


def test_run_forecast_persists_lightgbm_forecast_lines():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    load_test_dataset(db, target_date=target)

    run = run_forecast_for_date(target, db)
    run_line_count = len(run.lines)
    line_methods = [line.method for line in run.lines]
    line_count = db.query(ForecastLine).count()
    db.close()

    assert run.id is not None
    assert run.engine_name == ENGINE_NAME
    assert run.model_version == MODEL_METHOD
    assert run_line_count > 0
    assert line_count == run_line_count
    assert all(method == MODEL_METHOD for method in line_methods)


def test_run_forecast_fails_closed_when_business_data_is_missing():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    with pytest.raises(ReadinessError):
        run_forecast_for_date(date.today(), db)
    db.close()


def test_adjust_forecast_line_rejects_below_negative_100_percent():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    load_test_dataset(db, target_date=target)
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
    target = date.today()
    load_test_dataset(db, target_date=target)
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
