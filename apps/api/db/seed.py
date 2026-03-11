"""
Demo data seed script for BakeWise — Task 25
Outlet: Roti Lane Bakery
Outlets: KLCC, Bangsar, Mid Valley, Bukit Bintang, Damansara
30 days historical data with:
  - Bangsar: 15%+ waste rate on croissants
  - Mid Valley: morning stockout 3+ days/week
Run from apps/api directory: python -m db.seed
"""

import sys
import os
import random
from datetime import date, timedelta, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal, engine
from db.models import (
    Base, Outlet, SKU, Ingredient, RecipeBOM,
    SalesFact, InventorySnapshot, WasteLog
)

random.seed(42)

# ─── Master Data ──────────────────────────────────────────────────────────────

OUTLETS = [
    {"name": "Roti Lane KLCC",        "code": "RL-KLCC",  "address": "Suria KLCC, Kuala Lumpur"},
    {"name": "Roti Lane Bangsar",      "code": "RL-BGS",   "address": "Bangsar Village II, KL"},
    {"name": "Roti Lane Mid Valley",   "code": "RL-MV",    "address": "Mid Valley Megamall, KL"},
    {"name": "Roti Lane Bukit Bintang","code": "RL-BB",    "address": "Pavilion, Bukit Bintang, KL"},
    {"name": "Roti Lane Damansara",    "code": "RL-DMR",   "address": "Damansara Utama, PJ"},
]

SKUS = [
    {"name": "Butter Croissant",  "code": "SKU-CRO", "category": "Pastry",   "freshness_hours": 8,  "is_bestseller": True,  "safety_buffer_pct": 0.10, "price": 8.50},
    {"name": "Chocolate Muffin",  "code": "SKU-CMU", "category": "Muffin",   "freshness_hours": 12, "is_bestseller": False, "safety_buffer_pct": 0.10, "price": 6.00},
    {"name": "Banana Bread",      "code": "SKU-BNB", "category": "Bread",    "freshness_hours": 24, "is_bestseller": False, "safety_buffer_pct": 0.08, "price": 12.00},
    {"name": "Cheese Danish",     "code": "SKU-CDN", "category": "Pastry",   "freshness_hours": 8,  "is_bestseller": True,  "safety_buffer_pct": 0.10, "price": 9.00},
    {"name": "Cinnamon Roll",     "code": "SKU-CNR", "category": "Pastry",   "freshness_hours": 10, "is_bestseller": False, "safety_buffer_pct": 0.08, "price": 7.50},
    {"name": "Sourdough Loaf",    "code": "SKU-SDL", "category": "Bread",    "freshness_hours": 48, "is_bestseller": False, "safety_buffer_pct": 0.05, "price": 22.00},
    {"name": "Almond Croissant",  "code": "SKU-ACR", "category": "Pastry",   "freshness_hours": 8,  "is_bestseller": True,  "safety_buffer_pct": 0.10, "price": 9.50},
    {"name": "Matcha Latte",      "code": "SKU-MTL", "category": "Beverage", "freshness_hours": 4,  "is_bestseller": True,  "safety_buffer_pct": 0.15, "price": 14.00},
]

INGREDIENTS = [
    {"name": "Butter",          "code": "ING-BUT", "unit": "kg",  "stock_on_hand": 180.0, "reorder_point": 50.0,  "supplier_lead_time_hours": 24, "cost_per_unit": 28.0},
    {"name": "All-Purpose Flour","code": "ING-FLR", "unit": "kg",  "stock_on_hand": 400.0, "reorder_point": 100.0, "supplier_lead_time_hours": 48, "cost_per_unit": 3.5},
    {"name": "Eggs",            "code": "ING-EGG", "unit": "pcs", "stock_on_hand": 600.0, "reorder_point": 200.0, "supplier_lead_time_hours": 24, "cost_per_unit": 0.6},
    {"name": "Whole Milk",      "code": "ING-MLK", "unit": "L",   "stock_on_hand": 120.0, "reorder_point": 30.0,  "supplier_lead_time_hours": 24, "cost_per_unit": 5.5},
    {"name": "Dark Chocolate",  "code": "ING-CHO", "unit": "kg",  "stock_on_hand": 40.0,  "reorder_point": 10.0,  "supplier_lead_time_hours": 48, "cost_per_unit": 55.0},
    {"name": "Cheddar Cheese",  "code": "ING-CHE", "unit": "kg",  "stock_on_hand": 25.0,  "reorder_point": 8.0,   "supplier_lead_time_hours": 24, "cost_per_unit": 42.0},
    {"name": "Cinnamon Powder", "code": "ING-CIN", "unit": "kg",  "stock_on_hand": 15.0,  "reorder_point": 3.0,   "supplier_lead_time_hours": 72, "cost_per_unit": 80.0},
    {"name": "Almond",          "code": "ING-ALM", "unit": "kg",  "stock_on_hand": 20.0,  "reorder_point": 5.0,   "supplier_lead_time_hours": 48, "cost_per_unit": 48.0},
]

# ingredient quantities per 1 unit of each SKU (in ingredient unit)
RECIPE_BOM = {
    "SKU-CRO": [("ING-BUT", 0.060), ("ING-FLR", 0.120), ("ING-EGG", 1.0),   ("ING-MLK", 0.050)],
    "SKU-CMU": [("ING-FLR", 0.080), ("ING-EGG", 1.0),   ("ING-MLK", 0.060), ("ING-CHO", 0.030)],
    "SKU-BNB": [("ING-FLR", 0.150), ("ING-EGG", 2.0),   ("ING-MLK", 0.080), ("ING-BUT", 0.040)],
    "SKU-CDN": [("ING-BUT", 0.070), ("ING-FLR", 0.110), ("ING-EGG", 1.0),   ("ING-CHE", 0.040)],
    "SKU-CNR": [("ING-FLR", 0.100), ("ING-EGG", 1.0),   ("ING-BUT", 0.030), ("ING-CIN", 0.008)],
    "SKU-SDL": [("ING-FLR", 0.500), ("ING-MLK", 0.200), ("ING-BUT", 0.050)],
    "SKU-ACR": [("ING-BUT", 0.060), ("ING-FLR", 0.120), ("ING-EGG", 1.0),   ("ING-ALM", 0.025)],
    "SKU-MTL": [("ING-MLK", 0.250)],
}

# Base daily sales per outlet per SKU (units across all dayparts)
# [KLCC, Bangsar, MidValley, BukitBintang, Damansara]
BASE_DAILY_SALES = {
    "SKU-CRO": [45, 35, 50, 40, 30],
    "SKU-CMU": [30, 25, 35, 28, 20],
    "SKU-BNB": [15, 12, 18, 14, 10],
    "SKU-CDN": [25, 20, 30, 22, 18],
    "SKU-CNR": [20, 16, 22, 18, 14],
    "SKU-SDL": [8,  6,  10, 7,  5],
    "SKU-ACR": [12, 10, 14, 11, 8],
    "SKU-MTL": [55, 45, 65, 50, 35],
}

# Daypart split ratios [morning, midday, evening]
DAYPART_RATIOS = {
    "SKU-CRO": [0.55, 0.30, 0.15],
    "SKU-CMU": [0.35, 0.40, 0.25],
    "SKU-BNB": [0.20, 0.50, 0.30],
    "SKU-CDN": [0.45, 0.35, 0.20],
    "SKU-CNR": [0.40, 0.35, 0.25],
    "SKU-SDL": [0.30, 0.45, 0.25],
    "SKU-ACR": [0.50, 0.30, 0.20],
    "SKU-MTL": [0.50, 0.30, 0.20],
}

# Weekend multiplier
WEEKEND_MULTIPLIER = 1.25
DAYPARTS = ["morning", "midday", "evening"]


def get_sales_base(sku_code: str, outlet_idx: int, sale_date: date) -> int:
    base = BASE_DAILY_SALES[sku_code][outlet_idx]
    # Weekend boost
    if sale_date.weekday() >= 5:
        base = int(base * WEEKEND_MULTIPLIER)
    # Add noise
    base = max(0, int(base + random.gauss(0, base * 0.15)))
    return base


def clear_tables(db):
    db.query(WasteLog).delete()
    db.query(InventorySnapshot).delete()
    db.query(SalesFact).delete()
    db.commit()


def seed_master_data(db):
    # Idempotent: skip if already seeded
    if db.query(Outlet).count() > 0:
        print("  Master data already seeded. Skipping.")
        return

    print("  Seeding outlets...")
    outlet_objs = []
    for data in OUTLETS:
        o = Outlet(**data)
        db.add(o)
        outlet_objs.append(o)
    db.flush()

    print("  Seeding SKUs...")
    sku_objs = {}
    for data in SKUS:
        s = SKU(**data)
        db.add(s)
        db.flush()
        sku_objs[data["code"]] = s

    print("  Seeding ingredients...")
    ingredient_objs = {}
    for data in INGREDIENTS:
        i = Ingredient(**data)
        db.add(i)
        db.flush()
        ingredient_objs[data["code"]] = i

    print("  Seeding recipe BOM...")
    for sku_code, items in RECIPE_BOM.items():
        for ing_code, qty in items:
            bom = RecipeBOM(
                sku_id=sku_objs[sku_code].id,
                ingredient_id=ingredient_objs[ing_code].id,
                quantity_per_unit=qty,
                unit=ingredient_objs[ing_code].unit,
            )
            db.add(bom)

    db.commit()
    print("  Master data committed.")


def seed_sales_and_waste(db, outlets, skus):
    today = date.today()
    start_date = today - timedelta(days=30)

    # Outlet index lookup
    outlet_idx_map = {o.code: idx for idx, o in enumerate(outlets)}
    sku_map = {s.code: s for s in skus}

    BANGSAR_IDX = 1   # Bangsar — high croissant waste
    MV_IDX = 2        # Mid Valley — morning stockouts

    rows_sales = 0
    rows_waste = 0

    current = start_date
    while current < today:
        for sku in skus:
            sku_code = sku.code
            for outlet in outlets:
                o_idx = outlet_idx_map[outlet.code]
                total_base = get_sales_base(sku_code, o_idx, current)
                ratios = DAYPART_RATIOS[sku_code]

                daypart_sales = {}
                for dp_idx, dp in enumerate(DAYPARTS):
                    units = max(0, int(total_base * ratios[dp_idx]))
                    daypart_sales[dp] = units

                # ── Bangsar croissant overprep / waste ──────────────────────
                # Bangsar preps ~18% more than it sells → 15%+ waste rate
                if sku_code == "SKU-CRO" and outlet.code == "RL-BGS":
                    prep_total = int(total_base * 1.18)
                    waste_total = prep_total - total_base
                    # Log evening waste (end of day)
                    if waste_total > 0:
                        wl = WasteLog(
                            outlet_id=outlet.id,
                            sku_id=sku.id,
                            waste_date=current,
                            daypart="evening",
                            units_wasted=waste_total,
                            reason="End-of-day overproduction",
                        )
                        db.add(wl)
                        rows_waste += 1

                # ── Mid Valley morning stockout ─────────────────────────────
                # ~4 out of 7 days, morning croissants sell out early
                if sku_code == "SKU-CRO" and outlet.code == "RL-MV":
                    if current.weekday() in [0, 2, 4, 5]:  # Mon/Wed/Fri/Sat
                        # Artificial oversell (stockout day) — reduce stock to 0 early
                        daypart_sales["morning"] = int(daypart_sales["morning"] * 1.25)

                # Persist sales
                for dp in DAYPARTS:
                    sf = SalesFact(
                        outlet_id=outlet.id,
                        sku_id=sku.id,
                        sale_date=current,
                        daypart=dp,
                        units_sold=daypart_sales[dp],
                        revenue=round(daypart_sales[dp] * sku.price, 2),
                    )
                    db.add(sf)
                    rows_sales += 1

                # End-of-day inventory snapshot (estimated)
                eod_stock = max(0, random.randint(0, 3))
                inv = InventorySnapshot(
                    outlet_id=outlet.id,
                    sku_id=sku.id,
                    snapshot_date=current,
                    snapshot_time="eod",
                    units_on_hand=eod_stock,
                )
                db.add(inv)

        current += timedelta(days=1)
        if rows_sales % 1000 == 0 and rows_sales > 0:
            db.flush()

    db.commit()
    print(f"  Sales: {rows_sales} rows | Waste: {rows_waste} rows committed.")


def main():
    print("BakeWise seed starting...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_master_data(db)

        outlets = db.query(Outlet).all()
        skus = db.query(SKU).all()

        # Idempotent: only add sales if none exist
        if db.query(SalesFact).count() > 0:
            print("  Sales data already seeded. Skipping.")
        else:
            print("  Seeding 30-day sales, waste, inventory...")
            seed_sales_and_waste(db, outlets, skus)

        print("Done. Seed is idempotent — safe to re-run.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
