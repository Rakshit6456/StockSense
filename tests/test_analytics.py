"""Unit and integration tests for Person 2: Analytics Engine."""
from datetime import datetime, timedelta, timezone
import pytest

from backend import analytics, inventory as inv


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use an isolated SQLite test database for each test."""
    db_file = str(tmp_path / "test_analytics.db")
    monkeypatch.setenv("INVENTORY_DB", db_file)


# ---------------------------------------------------------------------------
# 1. average_daily_sales tests
# ---------------------------------------------------------------------------
def test_average_daily_sales_basic():
    """Verify average daily sales over a 30-day window with zero-sale days included."""
    inv.add_product("P1", "Product 1", price=100.0, stock=200)

    today = datetime.now(timezone.utc)
    # 3 sales totaling 60 units in the last 30 days
    inv.record_sale("P1", 20, timestamp=(today - timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S"))
    inv.record_sale("P1", 25, timestamp=(today - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"))
    inv.record_sale("P1", 15, timestamp=(today - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"))

    avg = analytics.average_daily_sales("P1", days=30)
    # 60 units / 30 days = 2.0 units/day
    assert isinstance(avg, float)
    assert avg == pytest.approx(2.0, rel=1e-3)


def test_average_daily_sales_window_cutoff():
    """Verify that transactions older than the requested lookback window are excluded."""
    inv.add_product("P1", "Product 1", price=100.0, stock=200)

    today = datetime.now(timezone.utc)
    # Sale 40 days ago (outside 30-day window)
    inv.record_sale("P1", 50, timestamp=(today - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S"))
    # Sale 5 days ago (inside window)
    inv.record_sale("P1", 15, timestamp=(today - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"))

    avg = analytics.average_daily_sales("P1", days=30)
    # Only 15 units / 30 days = 0.5 units/day
    assert avg == pytest.approx(0.5, rel=1e-3)


def test_average_daily_sales_no_sales():
    """Product with zero sales should return 0.0 float."""
    inv.add_product("P1", "Product 1", price=50.0, stock=20)
    avg = analytics.average_daily_sales("P1", days=30)
    assert isinstance(avg, float)
    assert avg == 0.0


def test_average_daily_sales_invalid_or_zero_days():
    """Zero or negative days parameter safely returns 0.0."""
    inv.add_product("P1", "Product 1", price=50.0, stock=20)
    assert analytics.average_daily_sales("P1", days=0) == 0.0
    assert analytics.average_daily_sales("P1", days=-5) == 0.0


def test_average_daily_sales_case_insensitivity_and_whitespace():
    """SKUs with lowercase letters or whitespace should normalize correctly."""
    inv.add_product("RICE01", "Basmati Rice", price=200.0, stock=50)
    inv.record_sale("RICE01", 30)

    avg = analytics.average_daily_sales("  rice01  ", days=30)
    assert avg == pytest.approx(1.0, rel=1e-3)


def test_average_daily_sales_unknown_sku_raises():
    """Querying a non-existent SKU raises ProductNotFoundError."""
    with pytest.raises(inv.ProductNotFoundError):
        analytics.average_daily_sales("DOES_NOT_EXIST", days=30)


# ---------------------------------------------------------------------------
# 2. calculate_reorder_point tests
# ---------------------------------------------------------------------------
def test_calculate_reorder_point_ceil_rounding():
    """Reorder point must use unrounded average daily sales and round UP via math.ceil."""
    # lead_time = 4, safety_stock = 2
    inv.add_product("P1", "Product 1", price=100.0, stock=100, lead_time_days=4, safety_stock=2)

    today = datetime.now(timezone.utc)
    # 10 units sold in 30 days => avg = 10 / 30 = 0.3333...
    # (0.3333... * 4) + 2 = 1.3333... + 2 = 3.3333... => ceil is 4
    inv.record_sale("P1", 10, timestamp=(today - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S"))

    rop = analytics.calculate_reorder_point("P1")
    assert isinstance(rop, int)
    assert rop == 4


def test_calculate_reorder_point_fractional_ceil_edge():
    """Even a small fractional demand pushes ROP to the next whole integer."""
    # lead_time = 3, safety_stock = 0
    inv.add_product("P2", "Product 2", price=50.0, stock=100, lead_time_days=3, safety_stock=0)

    today = datetime.now(timezone.utc)
    # 1 unit sold in 30 days => avg = 1 / 30 = 0.0333...
    # (0.0333... * 3) + 0 = 0.100 => ceil is 1
    inv.record_sale("P2", 1, timestamp=(today - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"))

    rop = analytics.calculate_reorder_point("P2")
    assert rop == 1


def test_calculate_reorder_point_zero_sales():
    """When sales are zero, ROP equals safety_stock."""
    inv.add_product("P3", "Product 3", price=50.0, stock=100, lead_time_days=5, safety_stock=12)
    rop = analytics.calculate_reorder_point("P3")
    assert rop == 12


# ---------------------------------------------------------------------------
# 3. get_reorder_list tests
# ---------------------------------------------------------------------------
def test_get_reorder_list_heapq_urgency_ordering():
    """Only products with stock < rop are listed, prioritized by largest shortage."""
    sid = inv.add_supplier("Supplier North")
    # P_URGENT: stock = 5, ROP = 25 (shortage = 20)
    inv.add_product("P_URGENT", "Urgent Item", price=100.0, stock=5, lead_time_days=5, safety_stock=25, supplier_id=sid)
    # P_MODERATE: stock = 8, ROP = 15 (shortage = 7)
    inv.add_product("P_MODERATE", "Moderate Item", price=50.0, stock=8, lead_time_days=3, safety_stock=15, supplier_id=sid)
    # P_HEALTHY: stock = 30, ROP = 10 (stock >= ROP -> excluded)
    inv.add_product("P_HEALTHY", "Healthy Item", price=20.0, stock=30, lead_time_days=2, safety_stock=10, supplier_id=sid)
    # P_BOUNDARY: stock = 10, ROP = 10 (stock == ROP -> excluded, strict stock < rop)
    inv.add_product("P_BOUNDARY", "Boundary Item", price=10.0, stock=10, lead_time_days=1, safety_stock=10, supplier_id=sid)

    reorder_list = analytics.get_reorder_list()
    assert len(reorder_list) == 2

    # Most urgent (largest shortage = 20) must be first
    assert reorder_list[0]["sku"] == "P_URGENT"
    assert reorder_list[0]["stock"] == 5
    assert reorder_list[0]["reorder_point"] == 25
    assert reorder_list[0]["supplier_name"] == "Supplier North"
    assert reorder_list[0]["suggested_order_qty"] >= 20

    # Second item (shortage = 7)
    assert reorder_list[1]["sku"] == "P_MODERATE"
    assert reorder_list[1]["stock"] == 8
    assert reorder_list[1]["reorder_point"] == 15


def test_get_reorder_list_all_healthy():
    """When all products have sufficient stock, return empty list."""
    inv.add_product("P1", "Item 1", price=50.0, stock=100, safety_stock=5)
    inv.add_product("P2", "Item 2", price=30.0, stock=50, safety_stock=10)
    assert analytics.get_reorder_list() == []


# ---------------------------------------------------------------------------
# 4. abc_analysis tests
# ---------------------------------------------------------------------------
def test_abc_analysis_pareto_classification():
    """Products ranked by revenue: A (<=80%), B (80-95%), C (>95%)."""
    inv.add_product("TOP", "Top Seller", price=800.0, stock=100)
    inv.add_product("MID", "Mid Seller", price=150.0, stock=100)
    inv.add_product("LOW", "Low Seller", price=50.0, stock=100)
    inv.add_product("ZERO", "Zero Seller", price=30.0, stock=100)

    # Total revenue = 8000 + 1500 + 500 + 0 = 10,000
    inv.record_sale("TOP", 10)   # 8,000  (80.0%) -> Class A
    inv.record_sale("MID", 10)   # 1,500  (cum 9,500 = 95.0%) -> Class B
    inv.record_sale("LOW", 10)   # 500    (cum 10,000 = 100.0%) -> Class C

    abc = analytics.abc_analysis()
    assert len(abc) == 4

    assert abc[0]["sku"] == "TOP"
    assert abc[0]["revenue"] == 8000.0
    assert abc[0]["cumulative_pct"] == 80.0
    assert abc[0]["abc_class"] == "A"

    assert abc[1]["sku"] == "MID"
    assert abc[1]["revenue"] == 1500.0
    assert abc[1]["cumulative_pct"] == 95.0
    assert abc[1]["abc_class"] == "B"

    assert abc[2]["sku"] == "LOW"
    assert abc[2]["revenue"] == 500.0
    assert abc[2]["cumulative_pct"] == 100.0
    assert abc[2]["abc_class"] == "C"

    assert abc[3]["sku"] == "ZERO"
    assert abc[3]["revenue"] == 0.0
    assert abc[3]["abc_class"] == "C"


def test_abc_analysis_single_product_dominant_90_percent():
    """Verify that a single product contributing 90% of total revenue is classified as Class A."""
    inv.add_product("DOMINANT", "Dominant Product", price=900.0, stock=50)
    inv.add_product("OTHER1", "Other Product 1", price=80.0, stock=50)
    inv.add_product("OTHER2", "Other Product 2", price=20.0, stock=50)

    # Total revenue = 9000 + 800 + 200 = 10,000
    # DOMINANT contributes 9,000 (90.0% of total revenue, > 80%)
    inv.record_sale("DOMINANT", 10)  # 9,000 (cum 90.0%)
    inv.record_sale("OTHER1", 10)    # 800   (cum 98.0%)
    inv.record_sale("OTHER2", 10)    # 200   (cum 100.0%)

    abc = analytics.abc_analysis()
    assert len(abc) == 3

    assert abc[0]["sku"] == "DOMINANT"
    assert abc[0]["revenue"] == 9000.0
    assert abc[0]["cumulative_pct"] == 90.0
    assert abc[0]["abc_class"] == "A"

    assert abc[1]["sku"] == "OTHER1"
    assert abc[1]["revenue"] == 800.0
    assert abc[1]["abc_class"] == "B"

    assert abc[2]["sku"] == "OTHER2"
    assert abc[2]["revenue"] == 200.0
    assert abc[2]["abc_class"] == "C"


def test_abc_analysis_zero_total_revenue():
    """Handle edge case where catalog has products but zero sales recorded."""
    inv.add_product("P1", "Item 1", price=100.0, stock=10)
    inv.add_product("P2", "Item 2", price=50.0, stock=10)

    abc = analytics.abc_analysis()
    assert len(abc) == 2
    for item in abc:
        assert item["revenue"] == 0.0
        assert item["cumulative_pct"] == 0.0
        assert item["abc_class"] == "C"


def test_abc_analysis_empty_catalog():
    """Empty database returns empty list."""
    assert analytics.abc_analysis() == []


# ---------------------------------------------------------------------------
# 5. dead_stock tests
# ---------------------------------------------------------------------------
def test_dead_stock_sorting_and_criteria():
    """Identify products with positive stock and zero sales in last N days, sorted by capital_tied_up."""
    # Stagnant 1: 10 units @ 100 cost = 1000 tied up
    inv.add_product("DEAD1", "Dead Item 1", price=150.0, cost=100.0, stock=10)
    # Stagnant 2: 5 units @ 400 cost = 2000 tied up (should be first)
    inv.add_product("DEAD2", "Dead Item 2", price=500.0, cost=400.0, stock=5)
    # Active: has sale yesterday -> excluded
    inv.add_product("ACTIVE", "Active Item", price=200.0, cost=120.0, stock=20)
    inv.record_sale("ACTIVE", 2)
    # Zero stock: no sales, but stock=0 -> excluded
    inv.add_product("ZERO_STOCK", "Empty Item", price=100.0, cost=80.0, stock=0)

    dead = analytics.dead_stock(days=30)
    assert len(dead) == 2

    # Higher capital tied up comes first
    assert dead[0]["sku"] == "DEAD2"
    assert dead[0]["capital_tied_up"] == 2000.0
    assert dead[0]["stock"] == 5
    assert dead[0]["last_sale"] == "Never"

    assert dead[1]["sku"] == "DEAD1"
    assert dead[1]["capital_tied_up"] == 1000.0
    assert dead[1]["last_sale"] == "Never"


def test_dead_stock_with_old_sale():
    """Product with sale 45 days ago is dead stock in a 30-day window."""
    today = datetime.now(timezone.utc)
    inv.add_product("OLD_SALE", "Old Seller", price=100.0, cost=60.0, stock=15)
    inv.record_sale("OLD_SALE", 2, timestamp=(today - timedelta(days=45)).strftime("%Y-%m-%d %H:%M:%S"))

    dead = analytics.dead_stock(days=30)
    assert len(dead) == 1
    assert dead[0]["sku"] == "OLD_SALE"
    # Initial stock was 15; selling 2 units decremented stock to 13.
    # Capital tied up = 13 * 60.0 = 780.0
    assert dead[0]["stock"] == 13
    assert dead[0]["capital_tied_up"] == 780.0
    assert dead[0]["last_sale"] == (today - timedelta(days=45)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# 6. moving_average tests
# ---------------------------------------------------------------------------
def test_moving_average_includes_zero_sale_days():
    """Daily sales series includes zero-sale calendar days between first and last sale."""
    inv.add_product("TREND", "Trend Item", price=50.0, cost=30.0, stock=100)

    # Day 1: 10 units @ 50 = 500 rev
    # Day 2: 0 units (gap day)
    # Day 3: 6 units @ 50 = 300 rev
    inv.record_sale("TREND", 10, timestamp="2026-10-01 10:00:00")
    inv.record_sale("TREND", 6, timestamp="2026-10-03 14:00:00")

    series = analytics.moving_average("TREND", window=3)
    assert len(series) == 3

    # Day 1 (2026-10-01)
    assert series[0]["date"] == "2026-10-01"
    assert series[0]["units_sold"] == 10
    assert series[0]["revenue"] == 500.0
    assert series[0]["moving_avg"] == 10.0

    # Day 2 (2026-10-02) -> zero-sale day
    assert series[1]["date"] == "2026-10-02"
    assert series[1]["units_sold"] == 0
    assert series[1]["revenue"] == 0.0
    # Window of 2 days: (10 + 0) / 2 = 5.0
    assert series[1]["moving_avg"] == 5.0

    # Day 3 (2026-10-03)
    assert series[2]["date"] == "2026-10-03"
    assert series[2]["units_sold"] == 6
    assert series[2]["revenue"] == 300.0
    # Window of 3 days: (10 + 0 + 6) / 3 = 5.33
    assert series[2]["moving_avg"] == 5.33


def test_moving_average_no_sales():
    """Product with no sales returns empty list."""
    inv.add_product("P1", "Item", price=10.0, stock=10)
    assert analytics.moving_average("P1") == []


def test_moving_average_window_rolling():
    """Verify sliding window drops oldest day once window size is reached."""
    inv.add_product("P1", "Item", price=10.0, stock=100)
    inv.record_sale("P1", 2, timestamp="2026-10-01 10:00:00")
    inv.record_sale("P1", 4, timestamp="2026-10-02 10:00:00")
    inv.record_sale("P1", 6, timestamp="2026-10-03 10:00:00")

    series = analytics.moving_average("P1", window=2)
    assert len(series) == 3

    # Day 1: [2] -> avg 2.0
    assert series[0]["moving_avg"] == 2.0
    # Day 2: [2, 4] -> avg 3.0
    assert series[1]["moving_avg"] == 3.0
    # Day 3: [4, 6] (window drops day 1) -> avg 5.0
    assert series[2]["moving_avg"] == 5.0
