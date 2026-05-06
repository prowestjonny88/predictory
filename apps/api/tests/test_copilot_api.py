from datetime import date
import json
import re

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import copilot.router as copilot_router
from db.database import Base, get_db
from factories import load_test_dataset, load_test_master_data
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


def _load_test_data(session):
    load_test_dataset(session)


def _fixed_llm(text: str = "LLM response"):
    return lambda _prompt, _text="": text


def _daily_actions_llm(prompt, _text=""):
    if "Candidate actions JSON" in prompt:
        action_ids = re.findall(r'"action_id":\s*"([^"]+)"', prompt)
        return json.dumps(
            [
                {
                    "action_id": action_id,
                    "action_text": f"Priority action for {action_id}",
                    "estimated_impact": "Protect readiness while preserving model plan values.",
                }
                for action_id in action_ids[:5]
            ]
        )
    if "Top actions JSON" in prompt:
        return (
            "Operations are broadly ready for service.\n\n"
            "Main risks are concentrated in the highest-ranked outlets and SKUs.\n\n"
            "Act on the ranked prep and reorder actions first."
        )
    return "LLM response"


def _prepare_planning_context(db, target_date: date) -> None:
    run_forecast_for_date(target_date, db)
    generate_prep_plan(target_date, db)
    recommend_replenishment(target_date, db)


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
    _load_test_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
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
        app.dependency_overrides.clear()


def test_explain_plan_supports_all_contexts_with_llm_text():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()

    _prepare_planning_context(db, target_date)

    from db.models import Outlet, SKU

    klcc = db.query(Outlet).filter(Outlet.name.like("%KLCC%")).first()
    bangsar = db.query(Outlet).filter(Outlet.name.like("%Bangsar%")).first()
    croissant = db.query(SKU).filter(SKU.name == "Butter Croissant").first()
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = _fixed_llm("Grounded LLM explanation")
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            test_cases = [
                ("forecast", klcc.id, croissant.id),
                ("prep", klcc.id, croissant.id),
                ("waste", bangsar.id, croissant.id),
                ("stockout", klcc.id, croissant.id),
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


def test_explain_plan_missing_data_returns_404():
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

    _override_app_db(SessionLocal)
    try:
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
            assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_explain_plan_forecast_mentions_contextual_drivers_when_present():
    SessionLocal = _build_session_factory()
    db = SessionLocal()

    from db.models import ForecastOverride, HolidayCalendar, Outlet, SKU, WeatherSnapshot

    target_date = date.today()
    _load_test_data(db)
    outlet = db.query(Outlet).filter(Outlet.code == "klcc_mall").first()
    sku = db.query(SKU).filter(SKU.code == "butter_croissant").first()
    db.add(
        HolidayCalendar(
            holiday_date=target_date,
            name="Festival Day",
            country_code="MY",
            holiday_type="Festival",
            demand_uplift_pct=5.0,
            source="test",
        )
    )
    weather = (
        db.query(WeatherSnapshot)
        .filter(WeatherSnapshot.outlet_id == outlet.id, WeatherSnapshot.target_date == target_date)
        .one()
    )
    weather.summary = "Light rain"
    weather.rain_mm = 3.4
    weather.temp_max_c = 31.2
    weather.adjustment_pct = -2.0
    weather.status = "applied"
    weather.source = "live"
    weather.raw_json = {"test": True}
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
    db.commit()
    run_forecast_for_date(target_date, db)
    outlet_id = outlet.id
    sku_id = sku.id
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = _fixed_llm("Holiday, weather adjustment, and manual override are reflected in the evidence.")
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/explain-plan",
                json={
                    "outlet_id": outlet_id,
                    "sku_id": sku_id,
                    "plan_date": target_date.isoformat(),
                    "context_type": "forecast",
                },
            )
            assert resp.status_code == 200
            explanation = resp.json()["explanation"].lower()
            assert "holiday" in explanation
            assert "weather adjustment" in explanation
            assert "manual override" in explanation
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_brief_returns_503_when_llm_unavailable():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()

    _prepare_planning_context(db, target_date)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda _prompt, _text="": (_ for _ in ()).throw(
        copilot_router.HTTPException(status_code=503, detail="LLM provider unavailable")
    )
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-brief",
                json={"brief_date": target_date.isoformat()},
            )
            assert resp.status_code == 503
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_brief_returns_503_when_llm_output_is_incomplete():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()

    _prepare_planning_context(db, target_date)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = _fixed_llm("Predictory Daily Operations Brief: 2026")
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-brief",
                json={"brief_date": target_date.isoformat()},
            )
            assert resp.status_code == 503
            assert "incomplete daily brief" in resp.json()["detail"]
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_run_scenario_handles_expected_inputs_without_db_writes():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()

    from db.models import PrepPlan, ReplenishmentPlan

    prep_plan_count_before = db.query(PrepPlan).count()
    repl_plan_count_before = db.query(ReplenishmentPlan).count()
    db.close()

    _override_app_db(SessionLocal)
    with TestClient(app) as client:
        scenarios = [
            "cut croissant prep at Bangsar Street by 15%",
            "increase croissant prep at KLCC Mall by 10%",
            "promo at KLCC Mall",
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
    _load_test_data(db)
    target_date = date.today()

    _prepare_planning_context(db, target_date)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = _daily_actions_llm
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


def test_daily_actions_uses_rules_based_output_when_llm_unavailable():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()

    _prepare_planning_context(db, target_date)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda _prompt, _text="": (_ for _ in ()).throw(
        copilot_router.HTTPException(status_code=503, detail="LLM provider unavailable")
    )
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 5},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["top_actions"]
            assert all(action["source_type"] == "rules_based" for action in payload["top_actions"])
            assert payload["brief"]
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_actions_targets_reference_valid_entities():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    _prepare_planning_context(db, target_date)

    from db.models import Ingredient, Outlet, SKU

    outlet_ids = {outlet.id for outlet in db.query(Outlet).all()}
    sku_ids = {sku.id for sku in db.query(SKU).all()}
    ingredient_ids = {ingredient.id for ingredient in db.query(Ingredient).all()}
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = _daily_actions_llm
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
    _load_test_data(db)
    target_date = date.today()
    _prepare_planning_context(db, target_date)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = _daily_actions_llm
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
    load_test_master_data(db)
    target_date = date.today()
    db.close()

    _override_app_db(SessionLocal)
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 5},
            )
            assert resp.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_daily_actions_dedupes_duplicate_prep_actions():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    _prepare_planning_context(db, target_date)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = _daily_actions_llm
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


def test_daily_plan_and_daily_actions_can_be_requested_for_same_date():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = _daily_actions_llm
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            daily_plan_resp = client.get(f"/api/v1/api/daily-plan/{target_date.isoformat()}")
            assert daily_plan_resp.status_code == 200
            daily_plan_payload = daily_plan_resp.json()
            assert "summary" in daily_plan_payload
            assert "top_actions" in daily_plan_payload["summary"]

            daily_actions_resp = client.post(
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 5},
            )
            assert daily_actions_resp.status_code == 200
            daily_actions_payload = daily_actions_resp.json()
            assert daily_actions_payload["date"] == target_date.isoformat()
            assert "top_actions" in daily_actions_payload
            assert "prep_actions" in daily_actions_payload
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_brief_localizes_llm_output():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    run_forecast_for_date(target_date, db)
    generate_prep_plan(target_date, db)
    recommend_replenishment(target_date, db)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda prompt, _text="": (
        "Ringkasan harian daripada LLM.\n\nRisiko utama diterangkan berdasarkan data operasi.\n\nPasukan perlu menyemak tindakan persediaan dan pengisian semula."
        if "Bahasa Melayu" in prompt
        else "æ¯æ—¥ç®€æŠ¥ LLM"
    )
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            ms_resp = client.post(
                "/api/v1/copilot/daily-brief",
                json={"brief_date": target_date.isoformat(), "language": "ms"},
            )
            zh_resp = client.post(
                "/api/v1/copilot/daily-brief",
                json={"brief_date": target_date.isoformat(), "language": "zh-CN"},
            )
            assert ms_resp.status_code == 200
            assert zh_resp.status_code == 200
            assert "Ringkasan harian" in ms_resp.json()["brief"]
            assert "LLM" in zh_resp.json()["brief"]
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_actions_localize_llm_output():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    _prepare_planning_context(db, target_date)
    db.close()

    def localized_daily_actions_llm(prompt, _text=""):
        if "Candidate actions JSON" in prompt:
            action_ids = re.findall(r'"action_id":\s*"([^"]+)"', prompt)
            text = "Kurangkan tindakan" if "Bahasa Melayu" in prompt else "å…³æ³¨è¡ŒåŠ¨"
            return json.dumps(
                [
                    {
                        "action_id": action_id,
                        "action_text": text,
                        "estimated_impact": "LLM impact",
                    }
                    for action_id in action_ids[:5]
                ]
            )
        if "Top actions JSON" in prompt:
            return "Tindakan harian LLM" if "Bahasa Melayu" in prompt else "æ¯æ—¥è¡ŒåŠ¨ LLM"
        return "LLM response"

    original = copilot_router._call_llm
    copilot_router._call_llm = localized_daily_actions_llm
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            ms_resp = client.post(
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 5, "language": "ms"},
            )
            zh_resp = client.post(
                "/api/v1/copilot/daily-actions",
                json={"target_date": target_date.isoformat(), "top_n": 5, "language": "zh-CN"},
            )
            assert ms_resp.status_code == 200
            assert zh_resp.status_code == 200
            assert "Tindakan harian" in ms_resp.json()["brief"]
            assert any(
                "Kurangkan" in action["action_text"] or "Pantau" in action["action_text"]
                for action in ms_resp.json()["top_actions"]
            )
            assert "LLM" in zh_resp.json()["brief"]
            assert zh_resp.json()["top_actions"]
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_scenario_supports_non_english_inputs():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    db.close()

    _override_app_db(SessionLocal)
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/copilot/run-scenario",
            json={
                "scenario_text": "Kurangkan prep croissant di Bangsar sebanyak 15%",
                "target_date": target_date.isoformat(),
                "language": "ms",
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert "Kurangkan prep" in payload["interpretation"] or "Teruskan" in payload["recommendation"]


def test_invalid_language_uses_english_prompt():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    _prepare_planning_context(db, target_date)
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = _fixed_llm(
        "Daily brief for English prompt.\n\nThe brief uses the provided forecast and risk data only.\n\nReview the highest priority actions before service."
    )
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/daily-brief",
                json={"brief_date": target_date.isoformat(), "language": "de"},
            )
            assert resp.status_code == 200
            assert "Daily brief for" in resp.json()["brief"]
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()
