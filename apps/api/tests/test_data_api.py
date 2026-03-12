from datetime import date
import random

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from db.models import AuditEvent, Outlet, PrepPlan, PrepPlanLine, SKU
from db.seed import seed_master_data, seed_sales_and_waste
from main import app


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


def test_upload_products_supports_upsert_and_create():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
        csv_content = "\n".join(
            [
                "sku_name,category,price,sku_code,freshness_hours,is_bestseller,safety_buffer_pct,is_active",
                "Butter Croissant,Pastry,9.25,SKU-CRO,8,true,10,true",
                "Blueberry Scone,Pastry,7.8,,10,false,0.12,true",
            ]
        )

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/imports/upload",
                params={"data_type": "products"},
                files={"file": ("products.csv", csv_content.encode("utf-8"), "text/csv")},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["rows_parsed"] == 2
            assert payload["rows_committed"] == 2
            assert payload["errors"] == []

        db = SessionLocal()
        croissant = db.query(SKU).filter(SKU.code == "SKU-CRO").first()
        assert croissant is not None
        assert croissant.price == 9.25

        scone = db.query(SKU).filter(SKU.name == "Blueberry Scone").first()
        assert scone is not None
        assert scone.code.startswith("SKU-")
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_upload_sales_and_inventory_accept_valid_rows():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
        sales_csv = "\n".join(
            [
                "outlet_code,sku_code,sale_date,daypart,units_sold,revenue",
                f"RL-KLCC,SKU-CRO,{date.today().isoformat()},morning,25,212.5",
            ]
        )
        inventory_csv = "\n".join(
            [
                "outlet_code,sku_code,snapshot_date,snapshot_time,units_on_hand",
                f"RL-KLCC,SKU-CRO,{date.today().isoformat()},eod,10",
            ]
        )

        with TestClient(app) as client:
            sales_resp = client.post(
                "/api/v1/imports/upload",
                params={"data_type": "sales"},
                files={"file": ("sales.csv", sales_csv.encode("utf-8"), "text/csv")},
            )
            assert sales_resp.status_code == 200
            assert sales_resp.json()["rows_committed"] == 1

            inv_resp = client.post(
                "/api/v1/imports/upload",
                params={"data_type": "inventory"},
                files={"file": ("inventory.csv", inventory_csv.encode("utf-8"), "text/csv")},
            )
            assert inv_resp.status_code == 200
            assert inv_resp.json()["rows_committed"] == 1
    finally:
        app.dependency_overrides.clear()


def test_upload_missing_required_columns_returns_422():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
        bad_products_csv = "\n".join(
            [
                "sku_name,category",
                "Blueberry Scone,Pastry",
            ]
        )

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/imports/upload",
                params={"data_type": "products"},
                files={"file": ("products.csv", bad_products_csv.encode("utf-8"), "text/csv")},
            )
            assert resp.status_code == 422
            assert "Missing required columns" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_catalog_endpoints_return_seeded_payloads():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)

    outlet = db.query(Outlet).first()
    sku = db.query(SKU).first()
    db.close()

    _override_app_db(SessionLocal)
    try:
        with TestClient(app) as client:
            outlets = client.get("/api/v1/outlets")
            assert outlets.status_code == 200
            assert len(outlets.json()) >= 5

            skus = client.get("/api/v1/skus")
            assert skus.status_code == 200
            assert len(skus.json()) >= 8

            ingredients = client.get("/api/v1/ingredients")
            assert ingredients.status_code == 200
            assert len(ingredients.json()) >= 5

            recipes = client.get("/api/v1/recipes")
            assert recipes.status_code == 200
            assert len(recipes.json()) > 0

            sales = client.get(
                "/api/v1/sales",
                params={
                    "outlet_id": outlet.id,
                    "sku_id": sku.id,
                    "start_date": (date.today().replace(day=1)).isoformat(),
                    "limit": 50,
                },
            )
            assert sales.status_code == 200

            inventory = client.get("/api/v1/inventory", params={"outlet_id": outlet.id})
            assert inventory.status_code == 200

            wastelogs = client.get(
                "/api/v1/wastelogs",
                params={"outlet_id": outlet.id},
            )
            assert wastelogs.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_ops_data_edit_approve_and_reapprove_conflict():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    seed_master_data(db)

    outlet = db.query(Outlet).first()
    sku = db.query(SKU).first()

    plan = PrepPlan(plan_date=date.today(), status="draft")
    db.add(plan)
    db.flush()

    line = PrepPlanLine(
        plan_id=plan.id,
        outlet_id=outlet.id,
        sku_id=sku.id,
        daypart="morning",
        recommended_units=10,
        edited_units=None,
        current_stock=2,
        status="pending",
    )
    db.add(line)
    db.commit()
    plan_id = plan.id
    line_id = line.id
    db.close()

    _override_app_db(SessionLocal)
    try:
        with TestClient(app) as client:
            edit_resp = client.patch(
                f"/api/v1/plans/prep/{plan_id}/lines/{line_id}",
                json={"edited_units": 12, "user_id": "tester"},
            )
            assert edit_resp.status_code == 200
            assert edit_resp.json()["edited_units"] == 12
            assert edit_resp.json()["status"] == "edited"

            approve_resp = client.post(
                f"/api/v1/plans/prep/{plan_id}/approve",
                json={"approved_by": "ops-manager"},
            )
            assert approve_resp.status_code == 200
            assert approve_resp.json()["status"] == "approved"

            conflict_resp = client.post(
                f"/api/v1/plans/prep/{plan_id}/approve",
                json={"approved_by": "ops-manager"},
            )
            assert conflict_resp.status_code == 409

        db = SessionLocal()
        audit_count = db.query(AuditEvent).count()
        assert audit_count >= 2
        db.close()
    finally:
        app.dependency_overrides.clear()
