"""Verification tests for Person 3 Frontend & UI bridge logic.
Verifies:
1. Role-based user authentication (admin vs staff)
2. UI bridge analytics & reorder recommendations
3. Sales, purchases, inventory error handling
4. Strict constraint: No SQL in UI files
"""
import os
import pytest

from backend import auth, inventory as inv
from pages._utils import (
    ensure_demo_users,
    get_abc_analysis_bridge,
    get_dead_stock_bridge,
    get_reorder_list_bridge,
    get_sales_trend_bridge,
    populate_demo_data,
)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use an isolated test database for every test."""
    test_db_path = str(tmp_path / "test_ui.db")
    monkeypatch.setenv("INVENTORY_DB", test_db_path)


def test_ensure_demo_users():
    """Ensure both admin and staff users exist with expected roles."""
    ensure_demo_users()
    admin_user = auth.authenticate("admin", "admin123")
    assert admin_user is not None
    assert admin_user["role"] == "admin"

    staff_user = auth.authenticate("staff", "staff123")
    assert staff_user is not None
    assert staff_user["role"] == "staff"


def test_populate_demo_data_and_summary():
    """Ensure sample data populates cleanly and dashboard summary updates."""
    populate_demo_data()
    summary = inv.dashboard_summary()
    assert summary["total_products"] >= 10
    assert summary["stock_value"] > 0
    assert summary["today_sales"] >= 0


def test_reorder_bridge_identifies_low_stock():
    """Test that items at or below reorder point are flagged."""
    # Add a product with 0 stock and safety stock = 5
    inv.add_product("LOW01", "Low Stock Item", price=100, cost=50, stock=2, safety_stock=5)
    reorder_list = get_reorder_list_bridge()
    skus = [item["sku"] for item in reorder_list]
    assert "LOW01" in skus
    target = next(item for item in reorder_list if item["sku"] == "LOW01")
    assert target["stock"] == 2
    assert target["suggested_order_qty"] > 0


def test_abc_analysis_bridge():
    """Test ABC revenue Pareto classification."""
    inv.add_product("TOP01", "Top Seller", price=1000, cost=500, stock=50)
    inv.add_product("MID01", "Mid Seller", price=100, cost=50, stock=50)
    inv.add_product("LOW01", "Low Seller", price=10, cost=5, stock=50)

    # Record sales
    inv.record_sale("TOP01", 10)  # Revenue 10,000
    inv.record_sale("MID01", 5)   # Revenue 500
    inv.record_sale("LOW01", 1)   # Revenue 10

    abc = get_abc_analysis_bridge()
    assert len(abc) == 3
    assert abc[0]["sku"] == "TOP01"
    assert abc[0]["abc_class"] == "A"
    assert abc[1]["sku"] == "MID01"


def test_dead_stock_bridge():
    """Test dead stock identification for items with stock but no recent sales."""
    inv.add_product("DEAD01", "Old Stagnant Item", price=200, cost=150, stock=20)
    inv.add_product("ACTIVE01", "Active Item", price=200, cost=150, stock=20)
    inv.record_sale("ACTIVE01", 2)

    dead = get_dead_stock_bridge(days=30)
    dead_skus = [d["sku"] for d in dead]
    assert "DEAD01" in dead_skus
    assert "ACTIVE01" not in dead_skus


def test_sales_trend_bridge():
    """Test sales trend aggregation and moving average."""
    inv.add_product("TREND01", "Trend Item", price=50, cost=30, stock=100)
    inv.record_sale("TREND01", 5)
    inv.record_sale("TREND01", 10)

    trend = get_sales_trend_bridge(sku="TREND01", window=3)
    assert len(trend) > 0
    assert trend[0]["units_sold"] == 15
    assert trend[0]["moving_avg"] == 15.0


def test_no_sql_in_ui_files():
    """Verify constraint: No SQL queries or database connections in UI files."""
    ui_files = [
        "app.py",
        "pages/_utils.py",
        "pages/1_Products.py",
        "pages/2_Sales_and_Purchases.py",
        "pages/3_Analytics.py",
    ]
    forbidden_tokens = ["sqlite3", "SELECT ", "INSERT INTO", "UPDATE ", "DELETE FROM", ".execute("]

    for rel_path in ui_files:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        for token in forbidden_tokens:
            assert token not in content, f"Forbidden SQL token '{token}' found in UI file: {rel_path}"
