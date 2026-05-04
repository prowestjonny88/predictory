"""Local demo operations seed for Predictory.

This script seeds the backend database with operational rows used by live API
flows: outlets, SKUs, ingredients, BOM, sales, inventory, waste, and holidays.
It does not regenerate the accepted ML artifact predictions in
apps/web/public/demo-data.

Run from apps/api:
    python -m db.seed
"""

import os
import random
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal, engine
from db.models import (
    Base,
    HolidayCalendar,
    Ingredient,
    InventorySnapshot,
    Outlet,
    RecipeBOM,
    SKU,
    SalesFact,
    WasteLog,
)

random.seed(42)

OUTLETS = [
    {"name": "KLCC Mall", "code": "klcc_mall", "address": "KLCC, Kuala Lumpur", "latitude": 3.1579, "longitude": 101.7123},
    {"name": "Bangsar Street", "code": "bangsar_street", "address": "Bangsar, Kuala Lumpur", "latitude": 3.1293, "longitude": 101.6782},
    {"name": "Mid Valley Mall", "code": "mid_valley_mall", "address": "Mid Valley City, Kuala Lumpur", "latitude": 3.1180, "longitude": 101.6761},
    {"name": "Mont Kiara Premium", "code": "mont_kiara_premium", "address": "Mont Kiara, Kuala Lumpur", "latitude": 3.1652, "longitude": 101.6524},
    {"name": "Subang Residential", "code": "subang_residential", "address": "Subang Jaya, Selangor", "latitude": 3.0567, "longitude": 101.5851},
]

SKUS = [
    {"name": "Blueberry Muffin", "code": "blueberry_muffin", "category": "Dessert", "freshness_hours": 12, "is_bestseller": False, "safety_buffer_pct": 0.10, "price": 3.80},
    {"name": "Brioche", "code": "brioche", "category": "Pastry", "freshness_hours": 10, "is_bestseller": False, "safety_buffer_pct": 0.08, "price": 4.10},
    {"name": "Brownie", "code": "brownie", "category": "Dessert", "freshness_hours": 18, "is_bestseller": False, "safety_buffer_pct": 0.08, "price": 4.50},
    {"name": "Butter Croissant", "code": "butter_croissant", "category": "Pastry", "freshness_hours": 8, "is_bestseller": True, "safety_buffer_pct": 0.10, "price": 4.25},
    {"name": "Cake Slice", "code": "cake_slice", "category": "Dessert", "freshness_hours": 8, "is_bestseller": False, "safety_buffer_pct": 0.10, "price": 7.90},
    {"name": "Chocolate Cookie", "code": "chocolate_cookie", "category": "Dessert", "freshness_hours": 18, "is_bestseller": False, "safety_buffer_pct": 0.08, "price": 3.20},
    {"name": "Coffee Bun / Sweet Bun", "code": "coffee_bun_sweet_bun", "category": "Pastry", "freshness_hours": 10, "is_bestseller": False, "safety_buffer_pct": 0.08, "price": 3.60},
    {"name": "Country Sourdough", "code": "country_sourdough", "category": "Bread", "freshness_hours": 24, "is_bestseller": True, "safety_buffer_pct": 0.08, "price": 8.50},
    {"name": "Fruit Tart", "code": "fruit_tart", "category": "Dessert", "freshness_hours": 8, "is_bestseller": False, "safety_buffer_pct": 0.10, "price": 6.90},
    {"name": "Ham & Cheese Sandwich", "code": "ham_cheese_sandwich", "category": "Savory", "freshness_hours": 8, "is_bestseller": False, "safety_buffer_pct": 0.10, "price": 8.90},
    {"name": "Pain au Chocolat", "code": "pain_au_chocolat", "category": "Pastry", "freshness_hours": 8, "is_bestseller": True, "safety_buffer_pct": 0.10, "price": 4.80},
    {"name": "Traditional Baguette", "code": "traditional_baguette", "category": "Bread", "freshness_hours": 24, "is_bestseller": True, "safety_buffer_pct": 0.08, "price": 6.50},
]

INGREDIENTS = [
    {"name": "Butter", "code": "ING-BUT", "unit": "kg", "stock_on_hand": 180.0, "reorder_point": 50.0, "supplier_lead_time_hours": 24, "cost_per_unit": 28.0},
    {"name": "All-Purpose Flour", "code": "ING-FLR", "unit": "kg", "stock_on_hand": 400.0, "reorder_point": 100.0, "supplier_lead_time_hours": 48, "cost_per_unit": 3.5},
    {"name": "Eggs", "code": "ING-EGG", "unit": "pcs", "stock_on_hand": 600.0, "reorder_point": 200.0, "supplier_lead_time_hours": 24, "cost_per_unit": 0.6},
    {"name": "Whole Milk", "code": "ING-MLK", "unit": "L", "stock_on_hand": 120.0, "reorder_point": 30.0, "supplier_lead_time_hours": 24, "cost_per_unit": 5.5},
    {"name": "Dark Chocolate", "code": "ING-CHO", "unit": "kg", "stock_on_hand": 40.0, "reorder_point": 10.0, "supplier_lead_time_hours": 48, "cost_per_unit": 55.0},
    {"name": "Cheddar Cheese", "code": "ING-CHE", "unit": "kg", "stock_on_hand": 25.0, "reorder_point": 8.0, "supplier_lead_time_hours": 24, "cost_per_unit": 42.0},
    {"name": "Cinnamon Powder", "code": "ING-CIN", "unit": "kg", "stock_on_hand": 15.0, "reorder_point": 3.0, "supplier_lead_time_hours": 72, "cost_per_unit": 80.0},
    {"name": "Almond", "code": "ING-ALM", "unit": "kg", "stock_on_hand": 20.0, "reorder_point": 5.0, "supplier_lead_time_hours": 48, "cost_per_unit": 48.0},
]

RECIPE_BOM = {
    "blueberry_muffin": [("ING-FLR", 0.080), ("ING-EGG", 1.0), ("ING-MLK", 0.055), ("ING-BUT", 0.025)],
    "brioche": [("ING-FLR", 0.110), ("ING-EGG", 1.0), ("ING-BUT", 0.055), ("ING-MLK", 0.040)],
    "brownie": [("ING-FLR", 0.055), ("ING-EGG", 1.0), ("ING-BUT", 0.040), ("ING-CHO", 0.045)],
    "butter_croissant": [("ING-BUT", 0.060), ("ING-FLR", 0.120), ("ING-EGG", 1.0), ("ING-MLK", 0.050)],
    "cake_slice": [("ING-FLR", 0.070), ("ING-EGG", 1.0), ("ING-MLK", 0.040), ("ING-BUT", 0.035)],
    "chocolate_cookie": [("ING-FLR", 0.040), ("ING-EGG", 0.5), ("ING-BUT", 0.030), ("ING-CHO", 0.030)],
    "coffee_bun_sweet_bun": [("ING-FLR", 0.085), ("ING-EGG", 1.0), ("ING-MLK", 0.045), ("ING-BUT", 0.025)],
    "country_sourdough": [("ING-FLR", 0.280), ("ING-MLK", 0.020)],
    "fruit_tart": [("ING-FLR", 0.070), ("ING-EGG", 1.0), ("ING-BUT", 0.045), ("ING-ALM", 0.020)],
    "ham_cheese_sandwich": [("ING-FLR", 0.090), ("ING-EGG", 0.5), ("ING-CHE", 0.045), ("ING-BUT", 0.020)],
    "pain_au_chocolat": [("ING-BUT", 0.055), ("ING-FLR", 0.110), ("ING-EGG", 1.0), ("ING-CHO", 0.035)],
    "traditional_baguette": [("ING-FLR", 0.260), ("ING-MLK", 0.010)],
}

# Base daily sales per outlet per SKU. Outlet order:
# KLCC, Bangsar, Mid Valley, Mont Kiara, Subang.
BASE_DAILY_SALES = {
    "blueberry_muffin": [22, 14, 18, 16, 10],
    "brioche": [16, 9, 13, 11, 7],
    "brownie": [14, 8, 12, 10, 6],
    "butter_croissant": [62, 36, 48, 44, 28],
    "cake_slice": [24, 16, 21, 19, 12],
    "chocolate_cookie": [18, 10, 15, 13, 8],
    "coffee_bun_sweet_bun": [28, 18, 24, 22, 14],
    "country_sourdough": [36, 24, 30, 28, 18],
    "fruit_tart": [20, 12, 18, 16, 9],
    "ham_cheese_sandwich": [26, 18, 24, 21, 13],
    "pain_au_chocolat": [48, 28, 40, 36, 22],
    "traditional_baguette": [110, 74, 96, 88, 58],
}

DAYPART_RATIOS = {
    "blueberry_muffin": [0.35, 0.40, 0.25],
    "brioche": [0.45, 0.35, 0.20],
    "brownie": [0.20, 0.45, 0.35],
    "butter_croissant": [0.55, 0.30, 0.15],
    "cake_slice": [0.20, 0.45, 0.35],
    "chocolate_cookie": [0.25, 0.40, 0.35],
    "coffee_bun_sweet_bun": [0.45, 0.35, 0.20],
    "country_sourdough": [0.40, 0.40, 0.20],
    "fruit_tart": [0.20, 0.45, 0.35],
    "ham_cheese_sandwich": [0.30, 0.50, 0.20],
    "pain_au_chocolat": [0.55, 0.30, 0.15],
    "traditional_baguette": [0.50, 0.35, 0.15],
}

WEEKEND_MULTIPLIER = 1.25
DAYPARTS = ["morning", "midday", "evening"]


def _seed_demo_holidays(db):
    if db.query(HolidayCalendar).count() > 0:
        return

    today = date.today()
    holidays = [
        HolidayCalendar(holiday_date=today + timedelta(days=1), name="Demo Public Holiday", country_code="MY", holiday_type="Public holiday", demand_uplift_pct=0.0, is_active=True, source="seeded_demo"),
        HolidayCalendar(holiday_date=today + timedelta(days=3), name="Demo Festival Day", country_code="MY", holiday_type="Festival", demand_uplift_pct=5.0, is_active=True, source="seeded_demo"),
        HolidayCalendar(holiday_date=date(today.year, 1, 1), name="New Year's Day", country_code="MY", holiday_type="Public holiday", demand_uplift_pct=15.0, is_active=True, source="seeded_demo"),
        HolidayCalendar(holiday_date=date(today.year, 2, 10), name="Chinese New Year", country_code="MY", holiday_type="Public holiday", demand_uplift_pct=35.0, is_active=True, source="seeded_demo"),
        HolidayCalendar(holiday_date=date(today.year, 12, 25), name="Christmas Day", country_code="MY", holiday_type="Public holiday", demand_uplift_pct=25.0, is_active=True, source="seeded_demo"),
        HolidayCalendar(holiday_date=today + timedelta(days=10), name="Upcoming Local Holiday", country_code="MY", holiday_type="Public holiday", demand_uplift_pct=20.0, is_active=True, source="seeded_demo"),
    ]
    db.add_all(holidays)
    db.commit()


def get_sales_base(sku_code: str, outlet_idx: int, sale_date: date, db=None) -> int:
    base = BASE_DAILY_SALES[sku_code][outlet_idx]
    if sale_date.weekday() >= 5:
        base = int(base * WEEKEND_MULTIPLIER)
    if db:
        holiday = db.query(HolidayCalendar).filter(HolidayCalendar.holiday_date == sale_date).first()
        if holiday and holiday.demand_uplift_pct:
            base = int(base * (1.0 + (holiday.demand_uplift_pct / 100.0)))
    return max(0, int(base + random.gauss(0, base * 0.15)))


def clear_tables(db):
    db.query(WasteLog).delete()
    db.query(InventorySnapshot).delete()
    db.query(SalesFact).delete()
    db.commit()


def _sync_existing_master_data(db) -> bool:
    if db.query(Outlet).count() == 0:
        return False

    print("  Master data already seeded. Synchronizing accepted demo catalog.")
    accepted_outlet_codes = {data["code"] for data in OUTLETS}
    accepted_sku_codes = {data["code"] for data in SKUS}

    for outlet in db.query(Outlet).all():
        outlet.is_active = outlet.code in accepted_outlet_codes
    for sku in db.query(SKU).all():
        sku.is_active = sku.code in accepted_sku_codes

    for data in OUTLETS:
        outlet = db.query(Outlet).filter(Outlet.code == data["code"]).first()
        if not outlet:
            outlet = Outlet(**data)
            db.add(outlet)
            db.flush()
        else:
            outlet.name = data["name"]
            outlet.address = data["address"]
            outlet.latitude = data["latitude"]
            outlet.longitude = data["longitude"]
            outlet.is_active = True

    for data in SKUS:
        sku = db.query(SKU).filter(SKU.code == data["code"]).first()
        if not sku:
            sku = SKU(**data)
            db.add(sku)
            db.flush()
        else:
            sku.name = data["name"]
            sku.category = data["category"]
            sku.freshness_hours = data["freshness_hours"]
            sku.is_bestseller = data["is_bestseller"]
            sku.safety_buffer_pct = data["safety_buffer_pct"]
            sku.price = data["price"]
            sku.is_active = True

    ingredient_objs = {}
    for data in INGREDIENTS:
        ingredient = db.query(Ingredient).filter(Ingredient.code == data["code"]).first()
        if not ingredient:
            ingredient = Ingredient(**data)
            db.add(ingredient)
            db.flush()
        else:
            ingredient.name = data["name"]
            ingredient.unit = data["unit"]
            ingredient.reorder_point = data["reorder_point"]
            ingredient.supplier_lead_time_hours = data["supplier_lead_time_hours"]
            ingredient.cost_per_unit = data["cost_per_unit"]
            ingredient.is_active = True
        ingredient_objs[data["code"]] = ingredient

    sku_objs = {sku.code: sku for sku in db.query(SKU).filter(SKU.code.in_(accepted_sku_codes)).all()}
    for sku_code, items in RECIPE_BOM.items():
        sku = sku_objs[sku_code]
        for ingredient_code, qty in items:
            ingredient = ingredient_objs[ingredient_code]
            existing = (
                db.query(RecipeBOM)
                .filter(RecipeBOM.sku_id == sku.id, RecipeBOM.ingredient_id == ingredient.id)
                .first()
            )
            if existing:
                existing.quantity_per_unit = qty
                existing.unit = ingredient.unit
            else:
                db.add(
                    RecipeBOM(
                        sku_id=sku.id,
                        ingredient_id=ingredient.id,
                        quantity_per_unit=qty,
                        unit=ingredient.unit,
                    )
                )

    db.commit()
    _seed_demo_holidays(db)
    return True


def seed_master_data(db):
    if _sync_existing_master_data(db):
        return

    print("  Seeding outlets...")
    for data in OUTLETS:
        db.add(Outlet(**data))
    db.flush()

    print("  Seeding SKUs...")
    sku_objs = {}
    for data in SKUS:
        sku = SKU(**data)
        db.add(sku)
        db.flush()
        sku_objs[data["code"]] = sku

    print("  Seeding ingredients...")
    ingredient_objs = {}
    for data in INGREDIENTS:
        ingredient = Ingredient(**data)
        db.add(ingredient)
        db.flush()
        ingredient_objs[data["code"]] = ingredient

    print("  Seeding recipe BOM...")
    for sku_code, items in RECIPE_BOM.items():
        for ingredient_code, qty in items:
            ingredient = ingredient_objs[ingredient_code]
            db.add(
                RecipeBOM(
                    sku_id=sku_objs[sku_code].id,
                    ingredient_id=ingredient.id,
                    quantity_per_unit=qty,
                    unit=ingredient.unit,
                )
            )

    db.commit()
    _seed_demo_holidays(db)
    print("  Master data committed.")


def seed_sales_and_waste(db, outlets, skus):
    today = date.today()
    start_date = today - timedelta(days=30)
    outlet_idx_map = {outlet.code: idx for idx, outlet in enumerate(outlets)}

    rows_sales = 0
    rows_waste = 0
    current = start_date
    while current < today:
        for sku in skus:
            sku_code = sku.code
            if sku_code not in BASE_DAILY_SALES:
                continue
            for outlet in outlets:
                if outlet.code not in outlet_idx_map:
                    continue
                daily_base = get_sales_base(sku_code, outlet_idx_map[outlet.code], current, db)
                ratios = DAYPART_RATIOS[sku_code]
                daypart_sales = {
                    daypart: max(0, int(daily_base * ratios[index]))
                    for index, daypart in enumerate(DAYPARTS)
                }
                total_base = sum(daypart_sales.values())

                if sku_code == "butter_croissant" and outlet.code == "bangsar_street":
                    prep_total = int(total_base * 1.25)
                    waste_total = prep_total - total_base
                    if waste_total > 0:
                        db.add(
                            WasteLog(
                                outlet_id=outlet.id,
                                sku_id=sku.id,
                                waste_date=current,
                                daypart="evening",
                                units_wasted=waste_total,
                                reason="End-of-day overproduction",
                            )
                        )
                        rows_waste += 1

                if sku_code == "butter_croissant" and outlet.code == "klcc_mall":
                    if current.weekday() in [0, 2, 4, 5]:
                        daypart_sales["morning"] = int(daypart_sales["morning"] * 1.25)

                for daypart in DAYPARTS:
                    units = daypart_sales[daypart]
                    db.add(
                        SalesFact(
                            outlet_id=outlet.id,
                            sku_id=sku.id,
                            sale_date=current,
                            daypart=daypart,
                            units_sold=units,
                            revenue=round(units * sku.price, 2),
                        )
                    )
                    rows_sales += 1

                db.add(
                    InventorySnapshot(
                        outlet_id=outlet.id,
                        sku_id=sku.id,
                        snapshot_date=current,
                        snapshot_time="eod",
                        units_on_hand=max(0, random.randint(0, 3)),
                    )
                )

        current += timedelta(days=1)
        if rows_sales % 1000 == 0 and rows_sales > 0:
            db.flush()

    db.commit()
    print(f"  Sales: {rows_sales} rows | Waste: {rows_waste} rows committed.")


def main():
    print("Predictory seed starting...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_master_data(db)
        outlets = db.query(Outlet).all()
        skus = db.query(SKU).all()

        accepted_outlet_ids = [outlet.id for outlet in outlets if outlet.code in {data["code"] for data in OUTLETS}]
        accepted_sku_ids = [sku.id for sku in skus if sku.code in {data["code"] for data in SKUS}]
        accepted_sales_count = (
            db.query(SalesFact)
            .filter(SalesFact.outlet_id.in_(accepted_outlet_ids), SalesFact.sku_id.in_(accepted_sku_ids))
            .count()
        )
        if accepted_sales_count > 0:
            print("  Accepted demo sales data already seeded. Skipping.")
        else:
            print("  Seeding 30-day sales, waste, inventory...")
            seed_sales_and_waste(
                db,
                [outlet for outlet in outlets if outlet.code in {data["code"] for data in OUTLETS}],
                [sku for sku in skus if sku.code in {data["code"] for data in SKUS}],
            )

        print("Done. Seed is idempotent and safe to re-run.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
