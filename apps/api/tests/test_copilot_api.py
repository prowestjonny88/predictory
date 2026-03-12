from datetime import date
import random

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import copilot.router as copilot_router
from db.database import Base, get_db
from db.seed import seed_master_data, seed_sales_and_waste
from forecasting.engine import run_forecast_for_date
from main import app
from planning.prep import generate_prep_plan
from planning.replenishment import recommend_replenishment


def _build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _seed_demo_data(session):
    random.seed(42)
    seed_master_data(session)

    from db.models import Outlet, SKU

    all_outlets = session.query(Outlet).all()
    all_skus = session.query(SKU).all()
    seed_sales_and_waste(session, all_outlets, all_skus)


def _override_app_db(SessionLocal):
    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db


def test_explain_plan_returns_404_for_unknown_outlet_or_sku():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda prompt, fallback="": fallback
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/explain-plan",
                json={
                    "outlet_id": 999,
                    "sku_id": 999,
                    "plan_date": date.today().isoformat(),
                    "context_type": "forecast",
                },
            )
            assert resp.status_code == 404
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_explain_plan_supports_all_contexts_with_fallback_text():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    target_date = date.today()

    run_forecast_for_date(target_date, db)
    generate_prep_plan(target_date, db)
    recommend_replenishment(target_date, db)

    from db.models import Outlet, SKU

    klcc = db.query(Outlet).filter(Outlet.name.like("%KLCC%")).first()
    bangsar = db.query(Outlet).filter(Outlet.name.like("%Bangsar%")).first()
    mid_valley = db.query(Outlet).filter(Outlet.name.like("%Mid Valley%")).first()
    croissant = db.query(SKU).filter(SKU.name == "Butter Croissant").first()
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda prompt, fallback="": fallback
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            test_cases = [
                ("forecast", klcc.id, croissant.id),
                ("prep", klcc.id, croissant.id),
                ("waste", bangsar.id, croissant.id),
                ("stockout", mid_valley.id, croissant.id),
                ("replenishment", klcc.id, croissant.id),
            ]

            for context_type, outlet_id, sku_id in test_cases:
                resp = client.post(
                    "/api/v1/copilot/explain-plan",
                    json={
                        "outlet_id": outlet_id,
                        "sku_id": sku_id,
                        "plan_date": target_date.isoformat(),
                        "context_type": context_type,
                    },
                )
                assert resp.status_code == 200
                payload = resp.json()
                assert payload["context_type"] == context_type
                assert payload["outlet_name"]
                assert payload["sku_name"] == "Butter Croissant"
                assert payload["explanation"]
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_explain_plan_missing_data_returns_graceful_fallback():
    SessionLocal = _build_session_factory()
    db = SessionLocal()

    from db.models import Outlet, SKU

    outlet = Outlet(name="Test Outlet", code="OUT-T")
    sku = SKU(
        name="Test SKU",
        code="SKU-T",
        category="Pastry",
        freshness_hours=8,
        is_bestseller=False,
        safety_buffer_pct=0.1,
        price=8.0,
    )
    db.add_all([outlet, sku])
    db.commit()
    db.refresh(outlet)
    db.refresh(sku)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda prompt, fallback="": fallback
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/explain-plan",
                json={
                    "outlet_id": outlet.id,
                    "sku_id": sku.id,
                    "plan_date": date.today().isoformat(),
                    "context_type": "forecast",
                },
            )
            assert resp.status_code == 200
            assert "No forecast data found" in resp.json()["explanation"]
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_brief_returns_deterministic_fallback_when_llm_unavailable():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    target_date = date.today()

    run_forecast_for_date(target_date, db)
    generate_prep_plan(target_date, db)
    recommend_replenishment(target_date, db)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda prompt, fallback="": fallback
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-brief",
                json={"brief_date": target_date.isoformat()},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["date"] == target_date.isoformat()
            assert "Total predicted sales are" in payload["brief"]
            assert payload["brief"].count("\n\n") == 2
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_run_scenario_handles_expected_inputs_without_db_writes():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    target_date = date.today()

    from db.models import PrepPlan, ReplenishmentPlan

    prep_plan_count_before = db.query(PrepPlan).count()
    repl_plan_count_before = db.query(ReplenishmentPlan).count()
    db.close()

    _override_app_db(SessionLocal)
    with TestClient(app) as client:
        scenarios = [
            "cut croissant prep at Bangsar by 15%",
            "increase croissant prep at KLCC by 10%",
            "promo at Mid Valley",
            "tell me something vague",
        ]

        for scenario_text in scenarios:
            resp = client.post(
                "/api/v1/copilot/run-scenario",
                json={
                    "scenario_text": scenario_text,
                    "target_date": target_date.isoformat(),
                },
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["scenario"] == scenario_text
            assert "baseline" in payload
            assert "modified" in payload
            assert "delta" in payload
            assert "recommendation" in payload
            assert "interpretation" in payload

    db = SessionLocal()
    assert db.query(PrepPlan).count() == prep_plan_count_before
    assert db.query(ReplenishmentPlan).count() == repl_plan_count_before
    db.close()
    app.dependency_overrides.clear()
