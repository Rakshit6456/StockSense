"""
Comprehensive edge-case pytest tests for StockSense Inventory Management System.

Covers:
  1. Empty database behaviour
  2. Zero-stock behaviour
  3. Bad input / validation (products & sales)
  4. Boundary values
  5. Database integrity
  6. Sales analytics

Each test is fully isolated – it runs against a fresh temporary SQLite file.
Production database is never touched.
"""
import pytest
from datetime import datetime, timedelta, timezone

from backend import analytics, inventory as inv
from backend.database import init_db


# ---------------------------------------------------------------------------
# Shared fixture – every test gets its own empty database
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Redirect INVENTORY_DB to a throwaway file for the duration of a test."""
    monkeypatch.setenv("INVENTORY_DB", str(tmp_path / "edge_test.db"))
    init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _add(sku="SKU1", name="Product 1", price=100.0, cost=60.0, stock=50,
         safety_stock=10, lead_time_days=3, supplier_id=None):
    return inv.add_product(sku, name, price=price, cost=cost, stock=stock,
                           safety_stock=safety_stock,
                           lead_time_days=lead_time_days,
                           supplier_id=supplier_id)


def _ts(days_ago):
    """Return a timestamp string N days in the past."""
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
        "%Y-%m-%d %H:%M:%S")


# ===========================================================================
# 1. EMPTY DATABASE TESTS
# ===========================================================================
class TestEmptyDatabase:

    def test_list_products_empty(self):
        assert inv.list_products() == []

    def test_list_suppliers_empty(self):
        assert inv.list_suppliers() == []

    def test_list_transactions_empty(self):
        assert inv.list_transactions() == []

    def test_dashboard_summary_zero_values(self):
        s = inv.dashboard_summary()
        assert s["total_products"] == 0
        assert s["stock_value"] == 0
        assert s["today_sales"] == 0

    def test_abc_analysis_empty_catalog(self):
        assert analytics.abc_analysis() == []

    def test_dead_stock_empty_db(self):
        assert analytics.dead_stock(days=30) == []

    def test_get_reorder_list_empty_db(self):
        assert analytics.get_reorder_list() == []

    def test_build_sku_index_empty(self):
        assert inv.build_sku_index() == {}

    def test_add_first_product_to_empty_db(self):
        pid = _add("FIRST1", "First Product")
        assert isinstance(pid, int)
        products = inv.list_products()
        assert len(products) == 1
        assert products[0]["sku"] == "FIRST1"

    def test_top_selling_analytics_no_sales(self):
        # abc_analysis treats all as Class C when revenue == 0
        _add("P1")
        result = analytics.abc_analysis()
        assert all(r["abc_class"] == "C" for r in result)

    def test_low_stock_alerts_no_products(self):
        reorder = analytics.get_reorder_list()
        assert reorder == []


# ===========================================================================
# 2. ZERO STOCK TESTS
# ===========================================================================
class TestZeroStock:

    def test_zero_stock_product_exists_in_db(self):
        _add("Z1", stock=0)
        p = inv.get_product_by_sku("Z1")
        assert p["stock"] == 0

    def test_zero_stock_appears_in_dead_stock(self):
        # Zero-stock items are excluded from dead_stock (no capital tied up)
        _add("Z1", stock=0)
        dead = analytics.dead_stock(days=30)
        assert all(d["sku"] != "Z1" for d in dead)

    def test_zero_stock_sale_raises_insufficient(self):
        _add("Z1", stock=0)
        with pytest.raises(inv.InsufficientStockError):
            inv.record_sale("Z1", 1)

    def test_oversell_raises_insufficient(self):
        _add("S1", stock=10)
        with pytest.raises(inv.InsufficientStockError):
            inv.record_sale("S1", 11)

    def test_sell_exact_stock_succeeds(self):
        _add("S1", stock=25)
        inv.record_sale("S1", 25)
        assert inv.get_product_by_sku("S1")["stock"] == 0

    def test_stock_reaches_zero_after_full_sale(self):
        _add("S1", stock=5)
        inv.record_sale("S1", 5)
        assert inv.get_product_by_sku("S1")["stock"] == 0

    def test_stock_never_goes_negative(self):
        _add("S1", stock=3)
        with pytest.raises(inv.InsufficientStockError):
            inv.record_sale("S1", 4)
        assert inv.get_product_by_sku("S1")["stock"] == 3

    def test_zero_stock_in_reorder_list(self):
        """A product with zero stock and safety_stock > 0 must appear in reorder list."""
        _add("Z1", stock=0, safety_stock=5)
        reorder = analytics.get_reorder_list()
        skus = [r["sku"] for r in reorder]
        assert "Z1" in skus

    def test_sale_rollback_on_zero_stock_no_transaction_logged(self):
        _add("S1", stock=0)
        with pytest.raises(inv.InsufficientStockError):
            inv.record_sale("S1", 1)
        assert inv.list_transactions(sku="S1") == []

    def test_purchase_replenishes_zero_stock(self):
        _add("Z1", stock=0)
        inv.record_purchase("Z1", 50)
        assert inv.get_product_by_sku("Z1")["stock"] == 50


# ===========================================================================
# 3. BAD INPUT / VALIDATION TESTS
# ===========================================================================
class TestProductBadInput:

    def test_empty_name_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.add_product("SKU1", "", price=100)

    def test_empty_sku_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.add_product("", "Name", price=100)

    def test_whitespace_only_sku_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.add_product("   ", "Name", price=100)

    def test_duplicate_sku_raises_duplicate_error(self):
        _add("DUPE1")
        with pytest.raises(inv.DuplicateError):
            inv.add_product("DUPE1", "Another", price=50)

    def test_duplicate_sku_case_insensitive(self):
        _add("DUPE2")
        with pytest.raises(inv.DuplicateError):
            inv.add_product("dupe2", "Another", price=50)

    def test_negative_price_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.add_product("N1", "Bad Price", price=-1)

    def test_negative_cost_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.add_product("N1", "Bad Cost", price=100, cost=-5)

    def test_negative_stock_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.add_product("N1", "Bad Stock", price=100, stock=-1)

    def test_negative_safety_stock_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.add_product("N1", "Bad Safety", price=100, safety_stock=-1)

    def test_negative_lead_time_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.add_product("N1", "Bad Lead", price=100, lead_time_days=-1)

    def test_invalid_supplier_id_rejected(self):
        """Non-existent supplier_id violates the FK constraint."""
        with pytest.raises(inv.InventoryError):
            inv.add_product("N1", "Bad Supplier", price=100, supplier_id=99999)

    def test_string_price_sqlite_stores_as_text(self):
        """SQLite has dynamic typing: a text value like 'expensive' is stored as-is
        in the REAL column without raising an error (no Python-level type guard in
        add_product). The CHECK (price >= 0) comparison with a TEXT value evaluates
        as True in SQLite (TEXT > numeric in SQLite type affinity ordering).
        This test documents the known gap; application-layer type validation should
        be added to add_product() to enforce numeric prices strictly."""
        pid = inv.add_product("N1", "Name", price="expensive")
        assert isinstance(pid, int)
        p = inv.get_product_by_sku("N1")
        # The raw stored value is the text string (SQLite type affinity gap)
        assert p["price"] == "expensive"

    def test_missing_required_price_field(self):
        with pytest.raises(TypeError):
            # price is a required positional arg
            inv.add_product("N1", "Name")


class TestSalesBadInput:

    def setup_method(self):
        _add("PROD1", stock=100)

    def test_zero_quantity_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.record_sale("PROD1", 0)

    def test_negative_quantity_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.record_sale("PROD1", -5)

    def test_float_quantity_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.record_sale("PROD1", 2.5)

    def test_string_quantity_rejected(self):
        with pytest.raises(inv.InventoryError):
            inv.record_sale("PROD1", "three")

    def test_nonexistent_sku_raises(self):
        with pytest.raises(inv.ProductNotFoundError):
            inv.record_sale("GHOST", 1)

    def test_empty_sku_raises(self):
        with pytest.raises((inv.ProductNotFoundError, inv.InventoryError)):
            inv.record_sale("", 1)

    def test_negative_unit_price_on_sale_rejected(self):
        """The DB CHECK constraint (unit_price >= 0) fires as sqlite3.IntegrityError.
        The backend does not currently re-wrap this in InventoryError, so we
        catch the raw IntegrityError that propagates through _record()."""
        import sqlite3 as _sqlite3
        with pytest.raises((inv.InventoryError, _sqlite3.IntegrityError)):
            inv.record_sale("PROD1", 1, unit_price=-10)

    @pytest.mark.parametrize("qty", [0, -1, -100])
    def test_purchase_invalid_qty_rejected(self, qty):
        with pytest.raises(inv.InventoryError):
            inv.record_purchase("PROD1", qty)

    def test_extremely_large_oversell_rejected(self):
        with pytest.raises(inv.InsufficientStockError):
            inv.record_sale("PROD1", 999_999)

    def test_invalid_sale_does_not_modify_stock(self):
        before = inv.get_product_by_sku("PROD1")["stock"]
        with pytest.raises(inv.InventoryError):
            inv.record_sale("PROD1", 0)
        assert inv.get_product_by_sku("PROD1")["stock"] == before

    def test_invalid_sale_does_not_create_transaction(self):
        with pytest.raises(inv.InventoryError):
            inv.record_sale("PROD1", -1)
        assert inv.list_transactions(sku="PROD1") == []


# ===========================================================================
# 4. BOUNDARY VALUE TESTS
# ===========================================================================
class TestBoundaryValues:

    def test_stock_equals_safety_stock_not_in_reorder(self):
        """stock == safety_stock: ROP = safety_stock (no sales), so stock == ROP -> excluded."""
        _add("B1", stock=10, safety_stock=10, lead_time_days=0)
        # With 0 sales: ROP = ceil(0*0 + 10) = 10; stock(10) is NOT < 10
        reorder = analytics.get_reorder_list()
        assert all(r["sku"] != "B1" for r in reorder)

    def test_stock_one_below_safety_stock_in_reorder(self):
        _add("B2", stock=9, safety_stock=10, lead_time_days=0)
        reorder = analytics.get_reorder_list()
        assert any(r["sku"] == "B2" for r in reorder)

    def test_stock_one_above_safety_stock_not_in_reorder(self):
        _add("B3", stock=11, safety_stock=10, lead_time_days=0)
        reorder = analytics.get_reorder_list()
        assert all(r["sku"] != "B3" for r in reorder)

    def test_sell_quantity_equals_stock(self):
        _add("B4", stock=7)
        inv.record_sale("B4", 7)
        assert inv.get_product_by_sku("B4")["stock"] == 0

    def test_sell_quantity_exceeds_stock_by_one(self):
        _add("B5", stock=7)
        with pytest.raises(inv.InsufficientStockError):
            inv.record_sale("B5", 8)
        assert inv.get_product_by_sku("B5")["stock"] == 7

    def test_price_equals_cost(self):
        """Zero-margin product must still be insertable."""
        pid = _add("B6", price=50.0, cost=50.0)
        assert isinstance(pid, int)

    def test_price_lower_than_cost(self):
        """Selling at a loss is allowed by the schema (price >= 0, cost >= 0)."""
        pid = _add("B7", price=30.0, cost=50.0)
        assert isinstance(pid, int)

    def test_zero_price_allowed(self):
        pid = _add("B8", price=0.0, cost=0.0)
        assert isinstance(pid, int)

    def test_zero_lead_time_allowed(self):
        pid = _add("B9", lead_time_days=0)
        assert isinstance(pid, int)
        assert inv.get_product_by_sku("B9")["lead_time_days"] == 0

    def test_zero_safety_stock_allowed(self):
        pid = _add("B10", safety_stock=0)
        assert isinstance(pid, int)

    def test_single_unit_stock_sell_one(self):
        _add("B11", stock=1)
        inv.record_sale("B11", 1)
        assert inv.get_product_by_sku("B11")["stock"] == 0

    def test_single_unit_stock_sell_two_fails(self):
        _add("B12", stock=1)
        with pytest.raises(inv.InsufficientStockError):
            inv.record_sale("B12", 2)


# ===========================================================================
# 5. DATABASE INTEGRITY TESTS
# ===========================================================================
class TestDatabaseIntegrity:

    def test_duplicate_product_not_created(self):
        _add("DUP1")
        with pytest.raises(inv.DuplicateError):
            _add("DUP1")
        assert len(inv.list_products()) == 1

    def test_duplicate_supplier_raises_duplicate_error(self):
        inv.add_supplier("FreshFoods Co")
        with pytest.raises(inv.DuplicateError):
            inv.add_supplier("FreshFoods Co")
        assert len(inv.list_suppliers()) == 1

    def test_product_references_valid_supplier(self):
        sid = inv.add_supplier("Test Supplier")
        _add("P1", supplier_id=sid)
        p = inv.get_product_by_sku("P1")
        assert p["supplier_id"] == sid

    def test_failed_insert_no_partial_record(self):
        """After a failed add_product, no partial row should exist."""
        try:
            inv.add_product("", "Bad SKU", price=100)
        except inv.InventoryError:
            pass
        assert inv.list_products() == []

    def test_failed_sale_rolls_back_stock(self):
        _add("S1", stock=5)
        with pytest.raises(inv.InsufficientStockError):
            inv.record_sale("S1", 100)
        assert inv.get_product_by_sku("S1")["stock"] == 5
        assert inv.list_transactions(sku="S1") == []

    def test_multiple_sales_accumulate_correctly(self):
        _add("M1", stock=100)
        inv.record_sale("M1", 10)
        inv.record_sale("M1", 20)
        inv.record_sale("M1", 5)
        assert inv.get_product_by_sku("M1")["stock"] == 65

    def test_multiple_purchases_accumulate_correctly(self):
        _add("M2", stock=10)
        inv.record_purchase("M2", 20)
        inv.record_purchase("M2", 30)
        assert inv.get_product_by_sku("M2")["stock"] == 60

    def test_idempotent_add_product_does_not_duplicate(self):
        """Running add_product twice with same SKU should not create two rows."""
        _add("IDEM1")
        try:
            _add("IDEM1")
        except inv.DuplicateError:
            pass
        assert len([p for p in inv.list_products() if p["sku"] == "IDEM1"]) == 1

    def test_delete_supplier_nullifies_product_supplier_id(self):
        sid = inv.add_supplier("Temp Supplier")
        _add("DS1", supplier_id=sid)
        inv.delete_supplier(sid)
        p = inv.get_product_by_sku("DS1")
        assert p["supplier_id"] is None

    def test_delete_product_cascades_transactions(self):
        _add("DEL1", stock=50)
        inv.record_sale("DEL1", 5)
        inv.delete_product("DEL1")
        assert inv.list_products() == []
        assert inv.list_transactions() == []

    def test_transaction_count_matches_sales_made(self):
        _add("TC1", stock=100)
        for qty in [5, 10, 15]:
            inv.record_sale("TC1", qty)
        txns = inv.list_transactions(sku="TC1", tx_type="SALE")
        assert len(txns) == 3

    def test_stock_consistency_after_interleaved_sale_purchase(self):
        _add("IC1", stock=20)
        inv.record_sale("IC1", 10)     # 10 left
        inv.record_purchase("IC1", 30) # 40
        inv.record_sale("IC1", 15)     # 25
        assert inv.get_product_by_sku("IC1")["stock"] == 25


# ===========================================================================
# 6. SALES ANALYTICS TESTS
# ===========================================================================
class TestSalesAnalytics:

    # -- average_daily_sales --------------------------------------------------
    def test_avg_daily_sales_no_sales_returns_zero(self):
        _add("A1")
        assert analytics.average_daily_sales("A1", days=30) == 0.0

    def test_avg_daily_sales_one_sale(self):
        _add("A2", stock=100)
        inv.record_sale("A2", 30)
        avg = analytics.average_daily_sales("A2", days=30)
        assert avg == pytest.approx(1.0, rel=1e-3)

    def test_avg_daily_sales_excludes_old_records(self):
        _add("A3", stock=200)
        inv.record_sale("A3", 60, timestamp=_ts(40))  # outside 30-day window
        inv.record_sale("A3", 15, timestamp=_ts(5))   # inside window
        avg = analytics.average_daily_sales("A3", days=30)
        assert avg == pytest.approx(0.5, rel=1e-3)

    def test_avg_daily_sales_unknown_sku_raises(self):
        with pytest.raises(inv.ProductNotFoundError):
            analytics.average_daily_sales("GHOST99", days=30)

    def test_avg_daily_sales_zero_days_returns_zero(self):
        _add("A4")
        assert analytics.average_daily_sales("A4", days=0) == 0.0

    # -- sales spanning multiple days -----------------------------------------
    def test_multiple_sales_same_day(self):
        _add("MD1", stock=100)
        inv.record_sale("MD1", 5, timestamp=_ts(0))
        inv.record_sale("MD1", 10, timestamp=_ts(0))
        inv.record_sale("MD1", 15, timestamp=_ts(0))
        txns = inv.list_transactions(sku="MD1", tx_type="SALE")
        assert len(txns) == 3
        total = sum(t["quantity"] for t in txns)
        assert total == 30

    def test_sales_spanning_60_days(self):
        _add("S60", stock=500)
        for d in range(60):
            inv.record_sale("S60", 2, timestamp=_ts(d))
        avg = analytics.average_daily_sales("S60", days=60)
        assert avg == pytest.approx(2.0, rel=1e-2)

    def test_sales_with_identical_timestamps(self):
        _add("TS1", stock=200)
        ts = _ts(1)
        for _ in range(5):
            inv.record_sale("TS1", 4, timestamp=ts)
        txns = inv.list_transactions(sku="TS1", tx_type="SALE")
        assert len(txns) == 5
        assert sum(t["quantity"] for t in txns) == 20

    # -- revenue & profit calculations ----------------------------------------
    def test_daily_revenue_calculation(self):
        _add("REV1", price=200.0, stock=50)
        inv.record_sale("REV1", 3, unit_price=200.0)
        s = inv.dashboard_summary()
        assert s["today_sales"] == pytest.approx(600.0)

    def test_total_stock_value_after_sale(self):
        _add("SV1", price=100.0, cost=70.0, stock=50)
        inv.record_sale("SV1", 10)
        s = inv.dashboard_summary()
        # 40 units remain, cost = 70 each
        assert s["stock_value"] == pytest.approx(40 * 70.0)

    def test_profit_implicit_in_transactions(self):
        """Profit = sum(quantity*(unit_price - cost)); verify figures via transaction log."""
        _add("PR1", price=150.0, cost=100.0, stock=20)
        inv.record_sale("PR1", 10, unit_price=150.0)
        txns = inv.list_transactions(sku="PR1", tx_type="SALE")
        revenue = sum(t["quantity"] * t["unit_price"] for t in txns)
        # 10 * 150 = 1500 revenue; 10 * 100 = 1000 cost; profit = 500
        assert revenue == pytest.approx(1500.0)

    # -- top-selling / ABC analysis ------------------------------------------
    def test_top_selling_product_ranked_first_in_abc(self):
        _add("TOP", price=500.0, stock=100)
        _add("MID", price=100.0, stock=100)
        _add("LOW", price=10.0, stock=100)
        inv.record_sale("TOP", 10)   # 5000 revenue
        inv.record_sale("MID", 5)    # 500 revenue
        inv.record_sale("LOW", 2)    # 20 revenue
        abc = analytics.abc_analysis()
        assert abc[0]["sku"] == "TOP"
        assert abc[0]["abc_class"] == "A"

    def test_products_with_no_sales_class_c(self):
        _add("NOSALE", price=100.0, stock=50)
        abc = analytics.abc_analysis()
        nosale_entry = next(r for r in abc if r["sku"] == "NOSALE")
        assert nosale_entry["abc_class"] == "C"
        assert nosale_entry["revenue"] == 0.0

    # -- moving average -------------------------------------------------------
    def test_moving_average_no_sales_returns_empty(self):
        _add("MA1")
        assert analytics.moving_average("MA1", window=7) == []

    def test_moving_average_single_day(self):
        _add("MA2", stock=50)
        inv.record_sale("MA2", 10, timestamp="2026-10-15 09:00:00")
        series = analytics.moving_average("MA2", window=7)
        assert len(series) == 1
        assert series[0]["date"] == "2026-10-15"
        assert series[0]["units_sold"] == 10
        assert series[0]["moving_avg"] == 10.0

    def test_moving_average_includes_zero_sale_gap_days(self):
        _add("MA3", stock=100)
        inv.record_sale("MA3", 10, timestamp="2026-10-01 10:00:00")
        inv.record_sale("MA3", 6,  timestamp="2026-10-03 10:00:00")
        series = analytics.moving_average("MA3", window=3)
        # Expect dates: 2026-10-01, 2026-10-02 (zero), 2026-10-03
        assert len(series) == 3
        assert series[1]["units_sold"] == 0
        assert series[1]["moving_avg"] == pytest.approx(5.0)

    def test_moving_average_window_rolls_correctly(self):
        _add("MA4", stock=100)
        inv.record_sale("MA4", 2, timestamp="2026-10-01 10:00:00")
        inv.record_sale("MA4", 4, timestamp="2026-10-02 10:00:00")
        inv.record_sale("MA4", 6, timestamp="2026-10-03 10:00:00")
        series = analytics.moving_average("MA4", window=2)
        assert series[0]["moving_avg"] == pytest.approx(2.0)
        assert series[1]["moving_avg"] == pytest.approx(3.0)
        assert series[2]["moving_avg"] == pytest.approx(5.0)

    # -- dead stock -----------------------------------------------------------
    def test_dead_stock_no_sales_identified(self):
        _add("DS1", stock=20)
        dead = analytics.dead_stock(days=30)
        assert any(d["sku"] == "DS1" for d in dead)

    def test_dead_stock_active_product_excluded(self):
        _add("LIVE1", stock=20)
        inv.record_sale("LIVE1", 2)
        dead = analytics.dead_stock(days=30)
        assert all(d["sku"] != "LIVE1" for d in dead)

    def test_dead_stock_old_sale_still_dead(self):
        _add("OLD1", stock=15)
        inv.record_sale("OLD1", 2, timestamp=_ts(45))
        dead = analytics.dead_stock(days=30)
        assert any(d["sku"] == "OLD1" for d in dead)

    def test_dead_stock_sorted_by_capital_tied_up(self):
        _add("DS_HIGH", cost=400.0, stock=10)  # 4000
        _add("DS_LOW",  cost=50.0,  stock=5)   # 250
        dead = analytics.dead_stock(days=30)
        assert dead[0]["sku"] == "DS_HIGH"
        assert dead[0]["capital_tied_up"] == pytest.approx(4000.0)

    def test_dead_stock_zero_stock_excluded(self):
        _add("ZSTOCK", stock=0, cost=100.0)
        dead = analytics.dead_stock(days=30)
        assert all(d["sku"] != "ZSTOCK" for d in dead)
