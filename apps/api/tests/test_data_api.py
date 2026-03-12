from datetime import date
import random

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from db.models import AuditEvent, HolidayCalendar, Outlet, PrepPlan, PrepPlanLine, SKU, SalesFact
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


def test_upload_sales_supports_common_bakery_transaction_headers():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
        tx_csv = "\n".join(
            [
                "transactionno,items,datetime,daytype,daypart",
                "T-1001,Butter Croissant,2026-03-10 08:15:00,Weekday,morning",
                "T-1002,Butter Croissant,2026-03-10 12:10:00,Weekday,midday",
            ]
        )

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/imports/upload",
                params={"data_type": "sales", "default_outlet_code": "RL-KLCC"},
                files={"file": ("bakery_tx.csv", tx_csv.encode("utf-8"), "text/csv")},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["rows_parsed"] == 2
            assert payload["rows_committed"] == 2
            assert payload["errors"] == []
    finally:
        app.dependency_overrides.clear()


def test_upload_sales_can_auto_create_skus_and_map_daypart_aliases():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
        tx_csv = "\n".join(
            [
                "transactionno,items,datetime,daypart,daytype",
                "TX-1,Scandinavian,2016-10-30 13:05:00,Afternoon,Weekend",
                "TX-2,Hot chocolate,2016-10-30 20:15:00,Night,Weekend",
            ]
        )

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/imports/upload",
                params={
                    "data_type": "sales",
                    "default_outlet_code": "RL-KLCC",
                    "auto_create_skus": True,
                },
                files={"file": ("bakery_tx.csv", tx_csv.encode("utf-8"), "text/csv")},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["rows_parsed"] == 2
            assert payload["rows_committed"] == 2
            assert payload["errors"] == []

        db = SessionLocal()
        created = db.query(SKU).filter(SKU.name == "Scandinavian").first()
        assert created is not None
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_upload_sales_aggregates_duplicate_transaction_rows_for_same_key():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
        tx_csv = "\n".join(
            [
                "transactionno,items,datetime,daypart,daytype",
                "T-1,Bread,2016-10-30 09:58:11,Morning,Weekend",
                "T-2,Bread,2016-10-30 09:59:11,Morning,Weekend",
            ]
        )

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/imports/upload",
                params={
                    "data_type": "sales",
                    "default_outlet_code": "RL-KLCC",
                    "auto_create_skus": True,
                },
                files={"file": ("bakery_tx.csv", tx_csv.encode("utf-8"), "text/csv")},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["rows_parsed"] == 2
            assert payload["rows_committed"] == 2
            assert payload["errors"] == []

        db = SessionLocal()
        bread_sku = db.query(SKU).filter(SKU.name == "Bread").first()
        assert bread_sku is not None

        sales = (
            db.query(SalesFact)
            .join(Outlet, SalesFact.outlet_id == Outlet.id)
            .filter(
                Outlet.code == "RL-KLCC",
                SalesFact.sku_id == bread_sku.id,
                SalesFact.sale_date == date(2016, 10, 30),
                SalesFact.daypart == "morning",
            )
            .all()
        )
        assert len(sales) == 1
        assert sales[0].units_sold == 2
        db.close()
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


def test_upload_rejects_invalid_data_type_and_empty_file():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
        with TestClient(app) as client:
            invalid_type_resp = client.post(
                "/api/v1/imports/upload",
                params={"data_type": "pricing"},
                files={"file": ("products.csv", b"sku_name,category,price\nTest,Pastry,5", "text/csv")},
            )
            assert invalid_type_resp.status_code == 422
            assert "data_type must be one of" in invalid_type_resp.json()["detail"]

            empty_file_resp = client.post(
                "/api/v1/imports/upload",
                params={"data_type": "products"},
                files={"file": ("products.csv", b"", "text/csv")},
            )
            assert empty_file_resp.status_code == 400
            assert empty_file_resp.json()["detail"] == "Uploaded file is empty"
    finally:
        app.dependency_overrides.clear()


def test_upload_normalizes_headers_and_reports_row_level_errors():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
        csv_content = "\n".join(
            [
                " SKU_NAME , CATEGORY , PRICE , IS_ACTIVE , IS_BESTSELLER ",
                "Blueberry Scone,Pastry,7.8,true,false",
                "Bad Scone,Pastry,5.5,maybe,true",
                "Broken Price,Pastry,not-a-number,true,false",
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
            assert payload["rows_parsed"] == 3
            assert payload["rows_committed"] == 1
            assert any("Invalid boolean value" in err for err in payload["errors"])
            assert any("could not convert string to float" in err for err in payload["errors"])

        db = SessionLocal()
        assert db.query(SKU).filter(SKU.name == "Blueberry Scone").first() is not None
        assert db.query(SKU).filter(SKU.name == "Bad Scone").first() is None
        assert db.query(SKU).filter(SKU.name == "Broken Price").first() is None
        db.close()
    finally:
        app.dependency_overrides.clear()


def test_upload_sales_reports_unknown_codes_without_committing_rows():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
        sales_csv = "\n".join(
            [
                "outlet_code,sku_code,sale_date,daypart,units_sold,revenue",
                f"UNKNOWN,SKU-CRO,{date.today().isoformat()},morning,25,212.5",
                f"RL-KLCC,UNKNOWN,{date.today().isoformat()},morning,25,212.5",
            ]
        )

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/imports/upload",
                params={"data_type": "sales"},
                files={"file": ("sales.csv", sales_csv.encode("utf-8"), "text/csv")},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["rows_parsed"] == 2
            assert payload["rows_committed"] == 0
            assert len(payload["errors"]) == 2
            assert all("unknown outlet_code or sku_code" in err for err in payload["errors"])
    finally:
        app.dependency_overrides.clear()


def test_upload_holidays_supports_create_and_update():
    SessionLocal = _build_session_factory()
    db = SessionLocal()
    _seed_demo_data(db)
    db.close()

    _override_app_db(SessionLocal)
    try:
        csv_content = "\n".join(
            [
                "holiday_date,name,country_code,holiday_type,demand_uplift_pct,is_active",
                "2026-04-10,Demo Festival Day,MY,Festival,5,true",
                "2026-04-10,Demo Festival Day,MY,Festival,7,true",
            ]
        )

        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/imports/upload",
                params={"data_type": "holidays"},
                files={"file": ("holidays.csv", csv_content.encode("utf-8"), "text/csv")},
            )
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["rows_parsed"] == 2
            assert payload["rows_committed"] == 2

        db = SessionLocal()
        holiday = (
            db.query(HolidayCalendar)
            .filter(
                HolidayCalendar.name == "Demo Festival Day",
                HolidayCalendar.holiday_date == date(2026, 4, 10),
            )
            .one()
        )
        assert holiday.country_code == "MY"
        assert holiday.demand_uplift_pct == 7
        db.close()
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


def test_catalog_endpoints_return_empty_lists_gracefully():
    SessionLocal = _build_session_factory()

    _override_app_db(SessionLocal)
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/outlets").json() == []
            assert client.get("/api/v1/skus").json() == []
            assert client.get("/api/v1/ingredients").json() == []
            assert client.get("/api/v1/recipes").json() == []
            assert client.get("/api/v1/sales").json() == []
            assert client.get("/api/v1/inventory").json() == []
            assert client.get("/api/v1/wastelogs").json() == []
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


def test_ops_data_rejects_negative_edits_and_blocks_edit_after_approval():
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
            negative_resp = client.patch(
                f"/api/v1/plans/prep/{plan_id}/lines/{line_id}",
                json={"edited_units": -1, "user_id": "tester"},
            )
            assert negative_resp.status_code == 422
            assert "edited_units must be >= 0" in negative_resp.json()["detail"]

            approve_resp = client.post(
                f"/api/v1/plans/prep/{plan_id}/approve",
                json={"approved_by": "ops-manager"},
            )
            assert approve_resp.status_code == 200

            locked_resp = client.patch(
                f"/api/v1/plans/prep/{plan_id}/lines/{line_id}",
                json={"edited_units": 8, "user_id": "tester"},
            )
            assert locked_resp.status_code == 409
            assert "Cannot edit an approved plan" in locked_resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
