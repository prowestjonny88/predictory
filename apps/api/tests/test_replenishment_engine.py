from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base
from db.models import Ingredient, Outlet, PrepPlan, PrepPlanLine, RecipeBOM, SKU
from planning.replenishment import _classify_urgency, recommend_replenishment


def _build_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def test_classify_urgency_thresholds():
    assert _classify_urgency(stock=0.0, need=10.0, lead_time_hours=24) == "critical"
    assert _classify_urgency(stock=7.0, need=10.0, lead_time_hours=24) == "high"
    assert _classify_urgency(stock=9.0, need=10.0, lead_time_hours=24) == "medium"
    assert _classify_urgency(stock=10.0, need=10.0, lead_time_hours=24) == "low"


def test_long_lead_time_bumps_urgency():
    assert _classify_urgency(stock=7.5, need=10.0, lead_time_hours=48) == "critical"
    assert _classify_urgency(stock=9.5, need=10.0, lead_time_hours=48) == "high"


def test_recommend_replenishment_triggers_butter_reorder_from_croissant_prep():
    db = _build_session()
    target_date = date(2026, 3, 12)

    outlet = Outlet(name="Roti Lane KLCC", code="RL-KLCC")
    sku = SKU(
        name="Butter Croissant",
        code="SKU-CRO",
        category="Pastry",
        freshness_hours=8,
        is_bestseller=True,
        safety_buffer_pct=0.1,
        price=8.5,
    )
    butter = Ingredient(
        name="Butter",
        code="ING-BUT",
        unit="kg",
        stock_on_hand=1.0,
        reorder_point=0.5,
        supplier_lead_time_hours=24,
        cost_per_unit=28.0,
    )
    flour = Ingredient(
        name="Flour",
        code="ING-FLR",
        unit="kg",
        stock_on_hand=100.0,
        reorder_point=10.0,
        supplier_lead_time_hours=48,
        cost_per_unit=3.5,
    )
    db.add_all([outlet, sku, butter, flour])
    db.flush()

    db.add_all(
        [
            RecipeBOM(sku_id=sku.id, ingredient_id=butter.id, quantity_per_unit=0.06, unit="kg"),
            RecipeBOM(sku_id=sku.id, ingredient_id=flour.id, quantity_per_unit=0.12, unit="kg"),
        ]
    )

    prep_plan = PrepPlan(plan_date=target_date, status="draft")
    db.add(prep_plan)
    db.flush()
    db.add_all(
        [
            PrepPlanLine(
                plan_id=prep_plan.id,
                outlet_id=outlet.id,
                sku_id=sku.id,
                daypart="morning",
                recommended_units=20,
                current_stock=0,
                status="pending",
            ),
            PrepPlanLine(
                plan_id=prep_plan.id,
                outlet_id=outlet.id,
                sku_id=sku.id,
                daypart="midday",
                recommended_units=20,
                current_stock=0,
                status="pending",
            ),
        ]
    )
    db.commit()

    plan = recommend_replenishment(target_date, db)
    lines_by_name = {line.ingredient.name: line for line in plan.lines}

    butter_line = lines_by_name["Butter"]
    assert butter_line.need_qty == 2.4
    assert butter_line.stock_on_hand == 1.0
    assert butter_line.reorder_qty == 1.4
    assert butter_line.urgency == "critical"
    assert butter_line.driving_skus == ["Butter Croissant"]

    flour_line = lines_by_name["Flour"]
    assert flour_line.need_qty == 4.8
    assert flour_line.reorder_qty == 0.0
    assert flour_line.urgency == "low"
