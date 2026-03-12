import random
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alerts.stockout import detect_stockout_risk
from alerts.waste import detect_waste_risk
from db.database import Base, get_db
from db.models import (
    ForecastRun,
    Ingredient,
    InventorySnapshot,
    Outlet,
    PrepPlan,
    PrepPlanLine,
    ReplenishmentPlan,
    RecipeBOM,
    SKU,
    SalesFact,
)
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

            for key in [
                "date",
                "prep_plan_id",
                "replenishment_plan_id",
                "forecasts",
                "prep_plan",
                "replenishment_plan",
                "waste_alerts",
                "stockout_alerts",
                "summary",
            ]:
                assert key in payload

            assert payload["date"] == target_date
            assert isinstance(payload["prep_plan_id"], int)
            assert isinstance(payload["replenishment_plan_id"], int)
            assert isinstance(payload["forecasts"], list)
            assert isinstance(payload["prep_plan"], list)
            assert isinstance(payload["replenishment_plan"], list)
            assert isinstance(payload["waste_alerts"], list)
            assert isinstance(payload["stockout_alerts"], list)

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


def test_daily_plan_reuses_existing_runs_and_plans_after_first_generation():
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
            first_resp = client.get(f"/api/v1/api/daily-plan/{target_date}")
            assert first_resp.status_code == 200

            db = SessionLocal()
            run_count = db.query(ForecastRun).count()
            prep_count = db.query(PrepPlan).count()
            repl_count = db.query(ReplenishmentPlan).count()
            db.close()

            assert run_count == 1
            assert prep_count == 1
            assert repl_count == 1

            second_resp = client.get(f"/api/v1/api/daily-plan/{target_date}")
            assert second_resp.status_code == 200

            db = SessionLocal()
            assert db.query(ForecastRun).count() == run_count
            assert db.query(PrepPlan).count() == prep_count
            assert db.query(ReplenishmentPlan).count() == repl_count
            db.close()
    finally:
        app.dependency_overrides.clear()


def test_stockout_keeps_checking_other_skus_after_ingredient_alert():
    SessionLocal = _build_session_factory()
    db = SessionLocal()

    outlet = Outlet(name="Edge Outlet", code="EDGE-OUT")
    sku_a = SKU(
        name="SKU A",
        code="EDGE-A",
        category="Pastry",
        freshness_hours=8,
        is_bestseller=False,
        safety_buffer_pct=0.1,
        price=5.0,
    )
    sku_b = SKU(
        name="SKU B",
        code="EDGE-B",
        category="Pastry",
        freshness_hours=8,
        is_bestseller=True,
        safety_buffer_pct=0.1,
        price=5.0,
    )
    ing = Ingredient(
        name="Butter",
        code="EDGE-ING",
        unit="kg",
        stock_on_hand=0.0,
        reorder_point=1.0,
        supplier_lead_time_hours=48,
        cost_per_unit=10.0,
    )
    db.add_all([outlet, sku_a, sku_b, ing])
    db.flush()

    db.add_all(
        [
            RecipeBOM(sku_id=sku_a.id, ingredient_id=ing.id, quantity_per_unit=1.0, unit="kg"),
            RecipeBOM(sku_id=sku_b.id, ingredient_id=ing.id, quantity_per_unit=1.0, unit="kg"),
        ]
    )

    target_date = date(2026, 3, 10)
    for i in range(1, 15):
        d = target_date - timedelta(days=i)
        db.add_all(
            [
                SalesFact(outlet_id=outlet.id, sku_id=sku_a.id, sale_date=d, daypart="morning", units_sold=8, revenue=40),
                SalesFact(outlet_id=outlet.id, sku_id=sku_a.id, sale_date=d, daypart="midday", units_sold=6, revenue=30),
                SalesFact(outlet_id=outlet.id, sku_id=sku_a.id, sale_date=d, daypart="evening", units_sold=4, revenue=20),
                SalesFact(outlet_id=outlet.id, sku_id=sku_b.id, sale_date=d, daypart="morning", units_sold=20, revenue=100),
                SalesFact(outlet_id=outlet.id, sku_id=sku_b.id, sale_date=d, daypart="midday", units_sold=10, revenue=50),
                SalesFact(outlet_id=outlet.id, sku_id=sku_b.id, sale_date=d, daypart="evening", units_sold=8, revenue=40),
            ]
        )

    db.add_all(
        [
            InventorySnapshot(outlet_id=outlet.id, sku_id=sku_a.id, snapshot_date=target_date, snapshot_time="eod", units_on_hand=5),
            InventorySnapshot(outlet_id=outlet.id, sku_id=sku_b.id, snapshot_date=target_date, snapshot_time="eod", units_on_hand=0),
        ]
    )

    prep = PrepPlan(plan_date=target_date, status="draft")
    db.add(prep)
    db.flush()
    db.add_all(
        [
            PrepPlanLine(plan_id=prep.id, outlet_id=outlet.id, sku_id=sku_a.id, daypart="morning", recommended_units=2, current_stock=5, status="pending"),
            PrepPlanLine(plan_id=prep.id, outlet_id=outlet.id, sku_id=sku_b.id, daypart="morning", recommended_units=0, current_stock=0, status="pending"),
        ]
    )
    db.commit()

    alerts = detect_stockout_risk(target_date, db)
    db.close()

    assert any(a.reason.startswith("Ingredient stock covers only") for a in alerts)
    assert any(
        a.sku_name == "SKU B"
        and a.affected_daypart == "morning"
        and "Morning stock" in a.reason
        for a in alerts
    )
