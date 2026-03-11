import random
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alerts.stockout import detect_stockout_risk
from alerts.waste import detect_waste_risk
from db.database import Base, get_db
from db.seed import seed_master_data, seed_sales_and_waste
from main import app
from planning.prep import generate_prep_plan


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


def test_seeded_alerts_flag_bangsar_waste_and_midvalley_stockout():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)

    target_date = date.today()
    generate_prep_plan(target_date, db)

    waste_alerts = detect_waste_risk(target_date, db)
    stockout_alerts = detect_stockout_risk(target_date, db)

    assert any(
        ("Bangsar" in a.outlet_name)
        and (a.sku_name == "Butter Croissant")
        and (a.daypart == "evening")
        and (a.risk_level == "high")
        for a in waste_alerts
    )
    assert any(
        ("Mid Valley" in a.outlet_name)
        and (a.sku_name == "Butter Croissant")
        and (a.affected_daypart == "morning")
        for a in stockout_alerts
    )

    db.close()


def test_daily_plan_api_returns_required_sections_and_plan_triggers():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    target_date = date.today().isoformat()
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
            resp = client.get(f"/api/v1/api/daily-plan/{target_date}")
            assert resp.status_code == 200
            payload = resp.json()

            for key in ["forecasts", "prep_plan", "replenishment_plan", "waste_alerts", "stockout_alerts", "summary"]:
                assert key in payload

            summary = payload["summary"]
            assert 0 <= summary["waste_risk_score"] <= 100
            assert 0 <= summary["stockout_risk_score"] <= 100
            assert len(summary["top_actions"]) <= 5
            assert isinstance(summary["at_risk_outlets"], list)

            prep_resp = client.post(f"/api/v1/plans/prep/run?target_date={target_date}")
            assert prep_resp.status_code == 200
            assert "plan_id" in prep_resp.json()

            repl_resp = client.post(f"/api/v1/plans/replenishment/run?target_date={target_date}")
            assert repl_resp.status_code == 200
            assert "plan_id" in repl_resp.json()
    finally:
        app.dependency_overrides.clear()
