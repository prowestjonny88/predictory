from datetime import date
import json
import re
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import copilot.router as copilot_router
import copilot.llm as copilot_llm
import copilot.daily_agent as daily_agent
import copilot.council.evidence as council_evidence
import copilot.council.router as council_router
from copilot.council.candidates import build_candidate_quantities
from db.database import Base, get_db
from db.models import DecisionAuditEvent, ForecastLine, ForecastRun, Outlet, PrepPlan, PrepPlanLine, SKU
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


def _council_judge_llm(prompt, _text=""):
    match = re.search(r"Candidate quantities JSON:\s*(\[.*?\])\s*Agent arguments JSON:", prompt, re.S)
    candidates = json.loads(match.group(1))
    selected = next((item for item in candidates if item["source"] == "optimizer"), candidates[0])
    return json.dumps(
        {
            "recommended_prep": selected["quantity"],
            "selected_candidate_source": selected["source"],
            "requires_confirmation": True,
            "reasoning_summary": "The council selected a server-generated candidate.",
            "primary_conflict": "Stockout risk and waste risk must be balanced.",
            "agent_consensus": "split",
        }
    )


def _prepare_planning_context(db, target_date: date) -> None:
    run_forecast_for_date(target_date, db)
    generate_prep_plan(target_date, db)
    recommend_replenishment(target_date, db)


def _prepare_council_context(db, target_date: date) -> PrepPlanLine:
    outlet = db.query(Outlet).filter(Outlet.code == "klcc_mall").first()
    sku = db.query(SKU).filter(SKU.code == "butter_croissant").first()
    run = ForecastRun(
        forecast_run_id=f"fr_council_{target_date.isoformat()}",
        forecast_date=target_date,
        engine_name="lightgbm_mlops_prototype",
        model_version="test",
    )
    db.add(run)
    db.flush()
    db.add(
        ForecastLine(
            run_id=run.id,
            outlet_id=outlet.id,
            sku_id=sku.id,
            morning=31,
            midday=18,
            evening=12,
            total=61,
            method="lightgbm_p50_v1",
        )
    )
    plan = PrepPlan(plan_date=target_date, status="draft")
    db.add(plan)
    db.flush()
    line = PrepPlanLine(
        plan_id=plan.id,
        outlet_id=outlet.id,
        sku_id=sku.id,
        daypart="morning",
        recommended_units=35,
        current_stock=4,
        status="pending",
        rationale_json={"source": "test"},
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def _patch_council_band():
    original_evidence = council_evidence.band_for_prep_line
    original_router = council_router.band_for_prep_line

    def fake_band(**_kwargs):
        return SimpleNamespace(p10=10.0, p50=31.0, p90=64.0, source="test")

    council_evidence.band_for_prep_line = fake_band
    council_router.band_for_prep_line = fake_band

    def restore():
        council_evidence.band_for_prep_line = original_evidence
        council_router.band_for_prep_line = original_router

    return restore


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
    copilot_router._call_llm = _fixed_llm(
        "Grounded Gemini explanation based only on backend evidence. "
        "It summarizes the supplied operational context without adding or changing any numbers."
    )
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
                assert payload["source_type"] == "llm_rephrased"
                assert payload["evidence"]["context_type"] == context_type
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
    copilot_router._call_llm = _fixed_llm(
        "Holiday, weather adjustment, and manual override are reflected in the evidence. "
        "The explanation stays grounded in those supplied drivers without adding new values."
    )
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


def test_manager_note_parse_uses_llm_validated_json():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    run_forecast_for_date(target_date, db)
    run = db.query(__import__("db.models", fromlist=["ForecastRun"]).ForecastRun).first()
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda _prompt, _text="": (
        '{"outlet_id":"KLCC Mall","daypart":"morning","sku_category":"Pastry",'
        '"suggested_adjustment_pct":15,"reason":"School group visiting",'
        '"requires_confirmation":true,"uncertainty_reason":null}'
    )
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/parse-manager-note",
                json={
                    "forecast_run_id": run.forecast_run_id,
                    "note": "Increase Pastry at KLCC Mall morning by 15% because a school group is visiting.",
                },
            )
            assert resp.status_code == 200
            parsed = resp.json()["parsed_adjustment"]
            assert parsed["parse_source"] == "llm_validated"
            assert parsed["outlet_id"] == "KLCC Mall"
            assert parsed["daypart"] == "morning"
            assert parsed["sku_category"] == "Pastry"
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_manager_note_parse_rejects_invalid_llm_target():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    run_forecast_for_date(target_date, db)
    run = db.query(__import__("db.models", fromlist=["ForecastRun"]).ForecastRun).first()
    db.close()

    original = copilot_router._call_llm
    copilot_router._call_llm = lambda _prompt, _text="": (
        '{"outlet_id":"Imaginary Outlet","daypart":"morning","sku_category":"Pastry",'
        '"suggested_adjustment_pct":15,"reason":"Bad target",'
        '"requires_confirmation":true,"uncertainty_reason":null}'
    )
    try:
        _override_app_db(SessionLocal)
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/parse-manager-note",
                json={"forecast_run_id": run.forecast_run_id, "note": "Increase pastry."},
            )
            assert resp.status_code == 422
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_explain_evidence_returns_503_when_llm_unavailable():
    original = copilot_router._call_llm
    copilot_router._call_llm = lambda _prompt, _text="": (_ for _ in ()).throw(
        copilot_router.HTTPException(status_code=503, detail="LLM provider unavailable")
    )
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/explain-evidence",
                json={"context_type": "kpi", "evidence": {"metric": "stockout", "value": 10}},
            )
            assert resp.status_code == 503
    finally:
        copilot_router._call_llm = original


def test_explain_evidence_prompt_forbids_number_invention():
    captured = {}
    original = copilot_router._call_llm

    def llm(prompt, _text=""):
        captured["prompt"] = prompt
        return (
            "Gemini explains the supplied backend evidence without changing values. "
            "It keeps the operational recommendation grounded in the provided metric and value."
        )

    copilot_router._call_llm = llm
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/explain-evidence",
                json={"context_type": "kpi", "evidence": {"metric": "stockout", "value": 10}},
            )
            assert resp.status_code == 200
            prompt = captured["prompt"]
            assert "Use only the provided JSON evidence" in prompt
            assert "Do not create, change, estimate, or infer new numbers" in prompt
            assert '"value": 10' in prompt
    finally:
        copilot_router._call_llm = original


def test_explain_evidence_prompt_translates_raw_backend_keys():
    captured = {}
    original = copilot_router._call_llm

    def llm(prompt, _text=""):
        captured["prompt"] = prompt
        return (
            "The backend daily-plan summary shows RM 30.49 of stockout exposure across the full plan. "
            "There are 180 actions awaiting manager review, so review the daily plan before service."
        )

    copilot_router._call_llm = llm
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/explain-evidence",
                json={
                    "context_type": "kpi",
                    "evidence": {
                        "metric": "full_plan_stockout_exposure_rm",
                        "value_rm": 30.49,
                        "scope": "full_plan",
                        "pending_action_count": 180,
                        "source": "backend_daily_plan_summary",
                    },
                },
            )
            assert resp.status_code == 200
            prompt = captured["prompt"]
            assert "Do not repeat raw JSON field names" in prompt
            assert "stockout exposure across the full plan" in prompt
            assert "actions awaiting manager review" in prompt
            assert "backend daily-plan summary" in prompt
            assert "What it means" in prompt
            assert "Why it matters" in prompt
            assert "Next step" in prompt
    finally:
        copilot_router._call_llm = original


def test_explain_evidence_rejects_raw_backend_key_leakage():
    original = copilot_router._call_llm
    copilot_router._call_llm = lambda _prompt, _text="": (
        "The backend_daily_plan_summary reports full_plan_stockout_exposure_rm value_rm of 30.49. "
        "The pending_action_count is 180 within the full_plan scope."
    )
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/explain-evidence",
                json={
                    "context_type": "kpi",
                    "evidence": {
                        "metric": "full_plan_stockout_exposure_rm",
                        "value_rm": 30.49,
                        "pending_action_count": 180,
                    },
                },
            )
            assert resp.status_code == 503
            assert "overly technical explanation" in resp.json()["detail"]
    finally:
        copilot_router._call_llm = original


def test_explain_evidence_rejects_truncated_llm_output():
    original = copilot_router._call_llm
    copilot_router._call_llm = lambda _prompt, _text="": (
        "For the morning daypart at KLCC Mall, the recommended prep for Butter Croissant "
        "is 35 units. This recommendation is based on"
    )
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/explain-evidence",
                json={"context_type": "recommendation", "evidence": {"recommended_prep": 35}},
            )
            assert resp.status_code == 503
            assert "incomplete or overly technical explanation" in resp.json()["detail"]
    finally:
        copilot_router._call_llm = original


def test_explain_evidence_retries_once_after_truncated_llm_output():
    original = copilot_router._call_llm
    calls = {"count": 0}

    def llm(_prompt, _text=""):
        calls["count"] += 1
        if calls["count"] == 1:
            return (
                "For the morning daypart at KLCC Mall, the recommended prep for Butter Croissant "
                "is 35 units. This recommendation is based on"
            )
        return (
            "For the morning daypart at KLCC Mall, the recommended prep for Butter Croissant is 35 units. "
            "The explanation stays grounded in the supplied recommendation evidence and does not add new values."
        )

    copilot_router._call_llm = llm
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/copilot/explain-evidence",
                json={"context_type": "recommendation", "evidence": {"recommended_prep": 35}},
            )
            assert resp.status_code == 200
            assert calls["count"] == 2
    finally:
        copilot_router._call_llm = original


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
            assert payload["llm_status"] == "success"
            assert payload["used_fallback"] is False
            assert payload["graph_trace"]
            assert all(action.get("priority_reason") for action in payload["top_actions"])
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
            assert payload["llm_status"] == "failed"
            assert payload["used_fallback"] is True
            assert payload["graph_trace"]
    finally:
        copilot_router._call_llm = original
        app.dependency_overrides.clear()


def test_daily_actions_skips_llm_when_no_candidate_actions(monkeypatch):
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    _prepare_planning_context(db, target_date)

    monkeypatch.setattr(daily_agent, "detect_waste_risk", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(daily_agent, "detect_stockout_risk", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(daily_agent, "_get_latest_replenishment_plan", lambda *_args, **_kwargs: SimpleNamespace(lines=[]))

    def llm(*_args, **_kwargs):
        raise AssertionError("LLM should not be called when there are no candidate actions")

    payload = daily_agent.generate_daily_actions(target_date, 5, db, llm)
    assert payload["top_actions"] == []
    assert payload["llm_status"] == "not_needed"
    assert payload["used_fallback"] is False
    assert any(step["node"] == "rules_brief_only" for step in payload["graph_trace"])
    db.close()


def test_daily_actions_drops_hallucinated_llm_action_ids():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _load_test_data(db)
    target_date = date.today()
    _prepare_planning_context(db, target_date)
    db.close()

    def bad_llm(prompt, _text="", **_kwargs):
        if "Candidate actions JSON" in prompt:
            return json.dumps({"top_actions": [{"action_id": "invented-action", "action_text": "Invented", "estimated_impact": "Invented"}]})
        return "This brief should not be used because ranking failed."

    _override_app_db(SessionLocal)
    try:
        with TestClient(app) as client:
            original = copilot_router._call_llm
            copilot_router._call_llm = bad_llm
            try:
                resp = client.post(
                    "/api/v1/copilot/daily-actions",
                    json={"target_date": target_date.isoformat(), "top_n": 5},
                )
            finally:
                copilot_router._call_llm = original
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["top_actions"]
            assert all(action["source_type"] == "rules_based" for action in payload["top_actions"])
            assert payload["llm_status"] == "failed"
            assert payload["used_fallback"] is True
    finally:
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


def test_council_candidate_generation_clamps_rounds_and_deduplicates():
    candidates = build_candidate_quantities(
        p10=2,
        p50=31,
        p90=64,
        opening_stock=4,
        optimizer_recommended_prep=35,
        batch_size=5,
    )
    quantities = [candidate.quantity for candidate in candidates]
    assert all(quantity >= 0 for quantity in quantities)
    assert len(quantities) == len(set(quantities))
    assert any(candidate.source == "optimizer" and candidate.quantity == 35 for candidate in candidates)
    assert any(candidate.source == "expected_demand" for candidate in candidates)
    assert any(candidate.source == "stockout_guardrail" for candidate in candidates)
    assert any(candidate.reason for candidate in candidates)


def test_council_review_returns_tool_backed_agent_arguments():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    try:
        _load_test_data(db)
        line = _prepare_council_context(db, target)
        restore_band = _patch_council_band()
        _override_app_db(SessionLocal)
        original = copilot_llm.call_llm
        copilot_llm.call_llm = _council_judge_llm
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/copilot/council/review",
                    json={"recommendation_id": str(line.id), "language": "en"},
                )
            assert response.status_code == 200
            payload = response.json()
            agents = {item["agent"] for item in payload["agent_arguments"]}
            assert {"Forecast Agent", "Stockout Guardian", "Waste Guardian", "Replenishment Agent"}.issubset(agents)
            assert payload["judge_recommendation"]["recommended_prep"] in [
                candidate["quantity"] for candidate in payload["candidate_quantities"]
            ]
            assert payload["source_type"] == "agent_council"
            assert any(item["node"] == "load_context" for item in payload["graph_trace"])
            assert any(item["node"] == "selected_replenishment_check" for item in payload["graph_trace"])
        finally:
            copilot_llm.call_llm = original
    finally:
        app.dependency_overrides.clear()
        restore_band()
        db.close()


def test_council_judge_invalid_output_falls_back_with_trace():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    try:
        _load_test_data(db)
        line = _prepare_council_context(db, target)
        restore_band = _patch_council_band()
        _override_app_db(SessionLocal)
        original = copilot_llm.call_llm
        copilot_llm.call_llm = lambda _prompt, _text="": json.dumps(
            {
                "recommended_prep": 999999,
                "selected_candidate_source": "hallucinated",
                "requires_confirmation": True,
                "reasoning_summary": "bad",
                "primary_conflict": None,
                "agent_consensus": "split",
            }
        )
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/copilot/council/review",
                    json={"recommendation_id": str(line.id), "language": "en"},
                )
            assert response.status_code == 200
            payload = response.json()
            assert payload["judge_recommendation"]["source"] == "fallback"
            assert any(item["agent"] == "Judge Agent" and item["source"] == "fallback" for item in payload["agent_trace"])
        finally:
            copilot_llm.call_llm = original
    finally:
        app.dependency_overrides.clear()
        restore_band()
        db.close()


def test_council_judge_mismatched_quantity_source_falls_back():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    try:
        _load_test_data(db)
        line = _prepare_council_context(db, target)
        restore_band = _patch_council_band()
        _override_app_db(SessionLocal)
        original = copilot_llm.call_llm

        def mismatched_llm(prompt, _text=""):
            match = re.search(r"Candidate quantities JSON:\s*(\[.*?\])\s*Agent arguments JSON:", prompt, re.S)
            candidates = json.loads(match.group(1))
            non_optimizer = next(item for item in candidates if item["source"] != "optimizer")
            return json.dumps(
                {
                    "recommended_prep": non_optimizer["quantity"],
                    "selected_candidate_source": "optimizer",
                    "requires_confirmation": True,
                    "reasoning_summary": "bad pair",
                    "primary_conflict": None,
                    "agent_consensus": "split",
                }
            )

        copilot_llm.call_llm = mismatched_llm
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/copilot/council/review",
                    json={"recommendation_id": str(line.id), "language": "en"},
                )
            assert response.status_code == 200
            payload = response.json()
            assert payload["judge_recommendation"]["source"] == "fallback"
            assert "mismatched quantity/source" in payload["judge_recommendation"]["reasoning_summary"]
        finally:
            copilot_llm.call_llm = original
    finally:
        app.dependency_overrides.clear()
        restore_band()
        db.close()


def test_council_review_exposes_current_plan_candidate_for_prior_edit():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    try:
        _load_test_data(db)
        line = _prepare_council_context(db, target)
        line.edited_units = line.recommended_units + 10
        line.status = "edited"
        db.add(line)
        db.commit()
        restore_band = _patch_council_band()
        _override_app_db(SessionLocal)
        original = copilot_llm.call_llm
        copilot_llm.call_llm = _council_judge_llm
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/copilot/council/review",
                    json={"recommendation_id": str(line.id), "language": "en"},
                )
            assert response.status_code == 200
            sources = {candidate["source"] for candidate in response.json()["candidate_quantities"]}
            assert "optimizer" in sources
            assert "current_plan" in sources
        finally:
            copilot_llm.call_llm = original
    finally:
        app.dependency_overrides.clear()
        restore_band()
        db.close()


def test_council_review_prefers_stored_optimizer_evidence():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    try:
        _load_test_data(db)
        line = _prepare_council_context(db, target)
        line.rationale_json = {
            "optimizer": {
                "batch_size": 7,
                "waste_cost": 1.23,
                "stockout_cost": 4.56,
                "financial_exposure": {
                    "stockout_exposure_rm": 12.3,
                    "waste_exposure_rm": 4.5,
                },
                "reason_summary": "Stored optimizer evidence.",
            }
        }
        db.add(line)
        db.commit()
        restore_band = _patch_council_band()
        _override_app_db(SessionLocal)
        original = copilot_llm.call_llm
        copilot_llm.call_llm = _council_judge_llm
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/copilot/council/review",
                    json={"recommendation_id": str(line.id), "language": "en"},
                )
            assert response.status_code == 200
            payload = response.json()
            assert not any(item["status"] == "warning" for item in payload["graph_trace"])
            expected = next(candidate for candidate in payload["candidate_quantities"] if candidate["source"] == "expected_demand")
            assert expected["evidence"]["batch_size"] == 7
            stockout = next(argument for argument in payload["agent_arguments"] if argument["agent"] == "Stockout Guardian")
            assert stockout["evidence"]["stockout_exposure_rm"] == 12.3
        finally:
            copilot_llm.call_llm = original
    finally:
        app.dependency_overrides.clear()
        restore_band()
        db.close()


def test_council_review_warns_when_optimizer_evidence_is_recalculated():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    try:
        _load_test_data(db)
        line = _prepare_council_context(db, target)
        restore_band = _patch_council_band()
        _override_app_db(SessionLocal)
        original = copilot_llm.call_llm
        copilot_llm.call_llm = _council_judge_llm
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/copilot/council/review",
                    json={"recommendation_id": str(line.id), "language": "en"},
                )
            assert response.status_code == 200
            assert any(item["status"] == "warning" for item in response.json()["graph_trace"])
        finally:
            copilot_llm.call_llm = original
    finally:
        app.dependency_overrides.clear()
        restore_band()
        db.close()


def test_council_review_with_note_adds_manager_context_candidate():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    try:
        _load_test_data(db)
        line = _prepare_council_context(db, target)
        restore_band = _patch_council_band()
        outlet = db.query(Outlet).filter(Outlet.id == line.outlet_id).first()
        sku = db.query(SKU).filter(SKU.id == line.sku_id).first()
        _override_app_db(SessionLocal)
        original = copilot_llm.call_llm
        copilot_llm.call_llm = _council_judge_llm
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/copilot/council/review-with-note",
                    json={
                        "recommendation_id": str(line.id),
                        "parsed_adjustment": {
                            "outlet_id": outlet.name,
                            "daypart": line.daypart,
                            "sku_category": sku.category,
                            "suggested_adjustment_pct": 15,
                            "reason": "school group visiting",
                            "requires_confirmation": True,
                            "parse_source": "llm_validated",
                        },
                        "language": "en",
                    },
                )
            assert response.status_code == 200
            after = response.json()["after_review"]
            before = response.json()["before_review"]
            assert before["recommendation_id"] == after["recommendation_id"]
            assert any(item["agent"] == "Manager Context Agent" for item in after["agent_arguments"])
            assert any(candidate["source"] == "manager_note_adjusted" for candidate in after["candidate_quantities"])
        finally:
            copilot_llm.call_llm = original
    finally:
        app.dependency_overrides.clear()
        restore_band()
        db.close()


def test_council_judge_prompt_includes_language_instruction():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    captured = {}
    try:
        _load_test_data(db)
        line = _prepare_council_context(db, target)
        restore_band = _patch_council_band()
        _override_app_db(SessionLocal)
        original = copilot_llm.call_llm

        def llm(prompt, _text=""):
            captured["prompt"] = prompt
            return _council_judge_llm(prompt, _text)

        copilot_llm.call_llm = llm
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/copilot/council/review",
                    json={"recommendation_id": str(line.id), "language": "ms"},
                )
            assert response.status_code == 200
            assert "Bahasa Melayu" in captured["prompt"]
            assert "Do not use alternate_sources" in captured["prompt"]
            assert '"agent_consensus": "split"' in captured["prompt"]
        finally:
            copilot_llm.call_llm = original
    finally:
        app.dependency_overrides.clear()
        restore_band()
        db.close()


def test_council_confirm_rejects_non_server_candidate():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    try:
        _load_test_data(db)
        line = _prepare_council_context(db, target)
        restore_band = _patch_council_band()
        _override_app_db(SessionLocal)
        original = copilot_llm.call_llm
        copilot_llm.call_llm = _council_judge_llm
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/copilot/council/confirm",
                    json={
                        "recommendation_id": str(line.id),
                        "selected_prep": 999999,
                        "operator_reason": "should be rejected",
                        "language": "en",
                    },
                )
            assert response.status_code == 422
        finally:
            copilot_llm.call_llm = original
    finally:
        app.dependency_overrides.clear()
        restore_band()
        db.close()


def test_council_confirm_applies_prep_edit_and_writes_audit_summary():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    target = date.today()
    try:
        _load_test_data(db)
        line = _prepare_council_context(db, target)
        restore_band = _patch_council_band()
        _override_app_db(SessionLocal)
        original = copilot_llm.call_llm
        copilot_llm.call_llm = _council_judge_llm
        try:
            with TestClient(app) as client:
                review = client.post(
                    "/api/v1/copilot/council/review",
                    json={"recommendation_id": str(line.id), "language": "en"},
                ).json()
                selected = review["judge_recommendation"]["recommended_prep"]
                response = client.post(
                    "/api/v1/copilot/council/confirm",
                    json={
                        "recommendation_id": str(line.id),
                        "selected_prep": selected,
                        "operator_reason": "Approved council recommendation.",
                        "language": "en",
                    },
                )
            assert response.status_code == 200
            payload = response.json()
            assert payload["application_mode"] == "prep_edit_only"
            assert payload["warnings"] == []
            assert payload["line_changes"][0]["after_prep"] == selected
            audit = db.query(DecisionAuditEvent).filter(DecisionAuditEvent.id == payload["audit_event_ids"][0]).first()
            assert audit is not None
            assert "agent_council" in audit.gemini_note_summary
        finally:
            copilot_llm.call_llm = original
    finally:
        app.dependency_overrides.clear()
        restore_band()
        db.close()
