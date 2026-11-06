"""
Idempotent seed script – adds 30 grocery products + 5 suppliers.
Safe to run multiple times: skips existing SKUs / supplier names.

Run from the StockSense root:
    python data/seed_products.py
"""
import random
import sys
import os

# Allow running from any working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, get_connection
from backend.inventory import (
    add_supplier, add_product, list_suppliers, list_products,
    DuplicateError,
)

random.seed(42)  # reproducible values

# ── 1. Suppliers ──────────────────────────────────────────────────────────────
SUPPLIERS = [
    {"name": "FreshFoods Co",          "phone": "9800001111", "email": "contact@freshfoods.in"},
    {"name": "AgroGlobal Ltd",         "phone": "9800002222", "email": "sales@agroglobal.in"},
    {"name": "Metro Wholesale",        "phone": "9800003333", "email": "orders@metrowholesale.in"},
    {"name": "DailyNeeds Distributors","phone": "9800004444", "email": "info@dailyneeds.in"},
    {"name": "SpiceWorld Suppliers",   "phone": "9800005555", "email": "spice@spiceworld.in"},
]

# ── 2. Products ───────────────────────────────────────────────────────────────
# supplier_key maps to the supplier name above
PRODUCTS = [
    # Dairy – FreshFoods Co
    dict(sku="MILK01",      name="Amul Toned Milk 1L",        category="Dairy",         price=68,  cost=55,  supplier="FreshFoods Co"),
    dict(sku="PANEER01",    name="Fresh Paneer 200g",          category="Dairy",         price=95,  cost=72,  supplier="FreshFoods Co"),
    dict(sku="BUTTER01",    name="Amul Butter 100g",           category="Dairy",         price=60,  cost=48,  supplier="FreshFoods Co"),
    dict(sku="CHEESE01",    name="Cheese Slices 200g",         category="Dairy",         price=145, cost=115, supplier="FreshFoods Co"),
    dict(sku="CURD01",      name="Fresh Curd 500g",            category="Dairy",         price=45,  cost=32,  supplier="FreshFoods Co"),
    # Snacks – Metro Wholesale
    dict(sku="BISCUIT01",   name="Parle-G Biscuits 800g",      category="Snacks",        price=80,  cost=65,  supplier="Metro Wholesale"),
    dict(sku="CHIPS01",     name="Potato Chips 100g",           category="Snacks",        price=40,  cost=28,  supplier="Metro Wholesale"),
    # Instant Food / Pantry – Metro Wholesale
    dict(sku="MAGGI01",     name="Instant Noodles Pack",        category="Instant Food",  price=70,  cost=52,  supplier="Metro Wholesale"),
    dict(sku="PASTA02",     name="Macaroni Pasta 500g",         category="Pantry",        price=110, cost=78,  supplier="Metro Wholesale"),
    dict(sku="KETCHUP01",   name="Tomato Ketchup 500g",         category="Pantry",        price=125, cost=90,  supplier="Metro Wholesale"),
    dict(sku="JAM01",       name="Mixed Fruit Jam 500g",        category="Pantry",        price=160, cost=120, supplier="Metro Wholesale"),
    # Pulses – AgroGlobal Ltd
    dict(sku="DAL01",       name="Toor Dal 1kg",                category="Pulses",        price=180, cost=145, supplier="AgroGlobal Ltd"),
    dict(sku="DAL02",       name="Moong Dal 1kg",               category="Pulses",        price=145, cost=115, supplier="AgroGlobal Ltd"),
    dict(sku="DAL03",       name="Chana Dal 1kg",               category="Pulses",        price=95,  cost=75,  supplier="AgroGlobal Ltd"),
    # Grains – AgroGlobal Ltd
    dict(sku="FLOUR01",     name="Whole Wheat Atta 5kg",        category="Grains",        price=260, cost=215, supplier="AgroGlobal Ltd"),
    dict(sku="MAIDA01",     name="Refined Flour 1kg",           category="Grains",        price=55,  cost=40,  supplier="AgroGlobal Ltd"),
    dict(sku="POHA01",      name="Flattened Rice 1kg",          category="Grains",        price=75,  cost=55,  supplier="AgroGlobal Ltd"),
    dict(sku="BESAN01",     name="Gram Flour 1kg",              category="Grains",        price=110, cost=85,  supplier="AgroGlobal Ltd"),
    # Beverages – FreshFoods Co
    dict(sku="COFFEE02",    name="Instant Coffee 100g",         category="Beverages",     price=220, cost=170, supplier="FreshFoods Co"),
    dict(sku="JUICE01",     name="Mixed Fruit Juice 1L",        category="Beverages",     price=120, cost=90,  supplier="FreshFoods Co"),
    dict(sku="SOFTDRINK01", name="Cola Drink 750ml",            category="Beverages",     price=45,  cost=32,  supplier="FreshFoods Co"),
    dict(sku="WATER01",     name="Packaged Water 1L",           category="Beverages",     price=20,  cost=12,  supplier="FreshFoods Co"),
    # Dry Fruits – AgroGlobal Ltd
    dict(sku="CASHEW01",    name="Cashews 250g",                category="Dry Fruits",    price=280, cost=220, supplier="AgroGlobal Ltd"),
    dict(sku="RAISIN01",    name="Raisins 250g",                category="Dry Fruits",    price=110, cost=80,  supplier="AgroGlobal Ltd"),
    dict(sku="WALNUT01",    name="Walnuts 250g",                category="Dry Fruits",    price=350, cost=280, supplier="AgroGlobal Ltd"),
    # Spices – SpiceWorld Suppliers
    dict(sku="TURMERIC01",  name="Turmeric Powder 200g",        category="Spices",        price=65,  cost=45,  supplier="SpiceWorld Suppliers"),
    dict(sku="CHILLI01",    name="Red Chilli Powder 200g",      category="Spices",        price=75,  cost=55,  supplier="SpiceWorld Suppliers"),
    dict(sku="CUMIN01",     name="Cumin Seeds 200g",            category="Spices",        price=90,  cost=65,  supplier="SpiceWorld Suppliers"),
    # Household – DailyNeeds Distributors
    dict(sku="DETERGENT01", name="Detergent Powder 1kg",        category="Household",     price=125, cost=95,  supplier="DailyNeeds Distributors"),
    # Personal Care – DailyNeeds Distributors
    dict(sku="SOAP01",      name="Bathing Soap Pack",           category="Personal Care", price=110, cost=80,  supplier="DailyNeeds Distributors"),
]


def main():
    init_db()

    # ── Step 1: Upsert suppliers ──────────────────────────────────────────────
    existing_suppliers = {s["name"]: s["id"] for s in list_suppliers()}
    suppliers_created = 0
    supplier_ids = {}

    for s in SUPPLIERS:
        if s["name"] in existing_suppliers:
            supplier_ids[s["name"]] = existing_suppliers[s["name"]]
        else:
            sid = add_supplier(s["name"], phone=s["phone"], email=s["email"])
            supplier_ids[s["name"]] = sid
            suppliers_created += 1

    # ── Step 2: Upsert products ───────────────────────────────────────────────
    existing_skus = {p["sku"] for p in list_products()}
    inserted = 0
    skipped = 0
    errors = []
    inserted_details = []

    with get_connection() as conn:
        for p in PRODUCTS:
            sku = p["sku"].strip().upper()
            if sku in existing_skus:
                skipped += 1
                continue
            stock       = random.randint(15, 100)
            safety_stk  = random.randint(5, 20)
            lead_time   = random.randint(2, 7)
            sup_id      = supplier_ids.get(p["supplier"])
            try:
                conn.execute(
                    """INSERT INTO products
                       (sku, name, category, price, cost, stock,
                        lead_time_days, safety_stock, supplier_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (sku, p["name"], p["category"], p["price"], p["cost"],
                     stock, lead_time, safety_stk, sup_id),
                )
                inserted += 1
                inserted_details.append(
                    dict(sku=sku, name=p["name"], stock=stock,
                         safety_stock=safety_stk, lead_time=lead_time)
                )
            except Exception as e:
                errors.append(f"{sku}: {e}")

    # ── Step 3: Final counts ──────────────────────────────────────────────────
    total_products = len(list_products())

    # ── Report ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  StockSense – Seed Script Results")
    print("=" * 60)
    print(f"  Suppliers created  : {suppliers_created}")
    print(f"  Products inserted  : {inserted}")
    print(f"  Products skipped   : {skipped}  (already existed)")
    print(f"  Total in DB now    : {total_products}")

    if inserted_details:
        print("\n  Newly added products:")
        print(f"  {'SKU':<14} {'Name':<30} {'Stock':>5} {'SafetyStk':>9} {'LeadDays':>8}")
        print("  " + "-" * 70)
        for d in inserted_details:
            print(f"  {d['sku']:<14} {d['name']:<30} {d['stock']:>5} "
                  f"{d['safety_stock']:>9} {d['lead_time']:>8}")

    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(f"    ✗ {e}")
    else:
        print("\n  No errors encountered. ✓")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

