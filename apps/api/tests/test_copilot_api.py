from datetime import date
import json
import random
import re

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


def test_daily_actions_returns_valid_schema_with_llm_rephrasing():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    target_date = date.today()

    run_forecast_for_date(target_date, db)
    generate_prep_plan(target_date, db)
    recommend_replenishment(target_date, db)
    db.close()

    def fake_llm(prompt, fallback=""):
        if "Candidate actions JSON" in prompt:
            action_ids = re.findall(r'"action_id":\s*"([^"]+)"', prompt)
            return json.dumps(
                [
                    {
                        "action_id": action_id,
                        "action_text": f"Priority action for {action_id}",
                        "estimated_impact": "Protect readiness while preserving deterministic plan values.",
                    }
                    for action_id in action_ids[:3]
                ]
            )
        if "Top actions JSON" in prompt:
            return (
                "Operations are broadly ready for service.\n\n"
                "Main risks are concentrated in the highest-ranked outlets and SKUs.\n\n"
                "Act on the ranked prep and reorder actions first."
            )
        return fallback

    original = copilot_router._call_llm
    copilot_router._call_llm = fake_llm
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 3},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["date"] == target_date.isoformat()
            assert payload["fallback_mode"] is False
            assert len(payload["top_actions"]) <= 3
            assert "brief" in payload
            assert "prep_actions" in payload
            assert "reorder_actions" in payload
            assert "risk_warnings" in payload
            assert "rebalance_suggestions" in payload
            assert payload["top_actions"]
            assert any(action["source_type"] == "llm_rephrased" for action in payload["top_actions"])
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_actions_fallback_mode_when_llm_unavailable():
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
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 5},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["fallback_mode"] is True
            assert payload["brief"].count("\n\n") == 2
            assert len(payload["top_actions"]) <= 5
            assert all(action["source_type"] == "deterministic" for action in payload["top_actions"])
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_actions_targets_reference_valid_entities():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    target_date = date.today()

    from db.models import Ingredient, Outlet, SKU

    outlet_ids = {outlet.id for outlet in db.query(Outlet).all()}
    sku_ids = {sku.id for sku in db.query(SKU).all()}
    ingredient_ids = {ingredient.id for ingredient in db.query(Ingredient).all()}
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda prompt, fallback="": fallback
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 5},
            )
            assert resp.status_code == 200
            payload = resp.json()

            all_actions = (
                payload["top_actions"]
                + payload["prep_actions"]
                + payload["reorder_actions"]
                + payload["risk_warnings"]
                + payload["rebalance_suggestions"]
            )
            for action in all_actions:
                target = action["target"]
                if target["outlet_id"] is not None:
                    assert target["outlet_id"] in outlet_ids
                if target["sku_id"] is not None:
                    assert target["sku_id"] in sku_ids
                if target["ingredient_id"] is not None:
                    assert target["ingredient_id"] in ingredient_ids
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_actions_caps_top_n_to_five():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    target_date = date.today()
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda prompt, fallback="": fallback
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 20},
            )
            assert resp.status_code == 200
            assert len(resp.json()["top_actions"]) <= 5
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_actions_handles_low_signal_dataset():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    seed_master_data(db)
    target_date = date.today()
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda prompt, fallback="": fallback
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 5},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["date"] == target_date.isoformat()
            assert payload["brief"]
            assert isinstance(payload["top_actions"], list)
            assert isinstance(payload["prep_actions"], list)
            assert isinstance(payload["reorder_actions"], list)
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_actions_dedupes_duplicate_prep_actions():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    target_date = date.today()
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda prompt, fallback="": fallback
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 5},
            )
            assert resp.status_code == 200
            prep_texts = [action["action_text"] for action in resp.json()["prep_actions"]]
            assert len(prep_texts) == len(set(prep_texts))
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()
