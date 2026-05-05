from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from db.models import (
    HolidayCalendar,
    Ingredient,
    InventorySnapshot,
    Outlet,
    RecipeBOM,
    SKU,
    SalesFact,
    WasteLog,
    WeatherSnapshot,
)


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

DAYPARTS = ("morning", "midday", "evening")


def load_test_master_data(db: Session) -> None:
    if db.query(Outlet).count() > 0:
        return

    outlet_by_code: dict[str, Outlet] = {}
    for data in OUTLETS:
        outlet = Outlet(**data)
        db.add(outlet)
        db.flush()
        outlet_by_code[outlet.code] = outlet

    sku_by_code: dict[str, SKU] = {}
    for data in SKUS:
        sku = SKU(**data)
        db.add(sku)
        db.flush()
        sku_by_code[sku.code] = sku

    ingredient_by_code: dict[str, Ingredient] = {}
    for data in INGREDIENTS:
        ingredient = Ingredient(**data)
        db.add(ingredient)
        db.flush()
        ingredient_by_code[ingredient.code] = ingredient

    for sku_code, items in RECIPE_BOM.items():
        for ingredient_code, quantity in items:
            ingredient = ingredient_by_code[ingredient_code]
            db.add(
                RecipeBOM(
                    sku_id=sku_by_code[sku_code].id,
                    ingredient_id=ingredient.id,
                    quantity_per_unit=quantity,
                    unit=ingredient.unit,
                )
            )

    today = date.today()
    db.add_all(
        [
            HolidayCalendar(holiday_date=today + timedelta(days=1), name="Public Holiday", country_code="MY", holiday_type="Public holiday", demand_uplift_pct=0.0, is_active=True, source="test_fixture"),
            HolidayCalendar(holiday_date=today + timedelta(days=3), name="Festival Day", country_code="MY", holiday_type="Festival", demand_uplift_pct=5.0, is_active=True, source="test_fixture"),
            HolidayCalendar(holiday_date=date(today.year, 1, 1), name="New Year's Day", country_code="MY", holiday_type="Public holiday", demand_uplift_pct=15.0, is_active=True, source="test_fixture"),
            HolidayCalendar(holiday_date=date(today.year, 12, 25), name="Christmas Day", country_code="MY", holiday_type="Public holiday", demand_uplift_pct=25.0, is_active=True, source="test_fixture"),
        ]
    )
    db.commit()


def load_test_weather(db: Session, target_date: date | None = None) -> None:
    load_test_master_data(db)
    target = target_date or date.today()
    outlets = db.query(Outlet).filter(Outlet.code.in_([data["code"] for data in OUTLETS])).all()
    for outlet in outlets:
        existing = (
            db.query(WeatherSnapshot)
            .filter(WeatherSnapshot.outlet_id == outlet.id, WeatherSnapshot.target_date == target)
            .first()
        )
        if existing:
            continue
        db.add(
            WeatherSnapshot(
                outlet_id=outlet.id,
                target_date=target,
                summary="Clear",
                rain_mm=0.0,
                temp_max_c=29.5,
                adjustment_pct=0.0,
                status="neutral",
                source="test_fixture",
                raw_json={"source": "test_fixture"},
            )
        )
    db.commit()


def load_test_history(db: Session, target_date: date | None = None, days: int = 35) -> None:
    load_test_master_data(db)
    rng = random.Random(42)
    target = target_date or date.today()
    start_date = target - timedelta(days=days)

    outlets = db.query(Outlet).filter(Outlet.code.in_([data["code"] for data in OUTLETS])).all()
    skus = db.query(SKU).filter(SKU.code.in_([data["code"] for data in SKUS])).all()
    outlet_idx = {data["code"]: index for index, data in enumerate(OUTLETS)}

    current = start_date
    while current < target:
        for sku in skus:
            ratios = DAYPART_RATIOS.get(sku.code)
            sales_base = BASE_DAILY_SALES.get(sku.code)
            if not ratios or not sales_base:
                continue
            for outlet in outlets:
                base = sales_base[outlet_idx[outlet.code]]
                if current.weekday() >= 5:
                    base = int(base * 1.25)
                daily_base = max(1, int(base + rng.gauss(0, base * 0.15)))
                daypart_sales = {
                    daypart: max(0, int(daily_base * ratios[index]))
                    for index, daypart in enumerate(DAYPARTS)
                }

                if sku.code == "butter_croissant" and outlet.code == "klcc_mall":
                    if current.weekday() in [0, 2, 4, 5]:
                        daypart_sales["morning"] = int(daypart_sales["morning"] * 1.25)
                if sku.code == "butter_croissant" and outlet.code == "bangsar_street":
                    total_base = sum(daypart_sales.values())
                    waste_total = max(0, int(total_base * 0.25))
                    if waste_total:
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

                for daypart, units in daypart_sales.items():
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

                if sku.code == "butter_croissant" and outlet.code == "klcc_mall" and (target - current).days in {1, 2, 3}:
                    units_on_hand = 0
                else:
                    units_on_hand = max(0, rng.randint(1, 6))
                db.add(
                    InventorySnapshot(
                        outlet_id=outlet.id,
                        sku_id=sku.id,
                        snapshot_date=current,
                        snapshot_time="eod",
                        units_on_hand=units_on_hand,
                    )
                )
        current += timedelta(days=1)

    db.commit()


def load_test_dataset(db: Session, target_date: date | None = None) -> None:
    load_test_master_data(db)
    load_test_history(db, target_date=target_date)
    load_test_weather(db, target_date=target_date)
