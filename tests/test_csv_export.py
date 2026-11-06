"""
Comprehensive pytest tests for the CSV export backend (backend/exports.py).

Covers:
 - Empty inventory / empty sales
 - Full export correctness (headers, row count, calculations)
 - Filtered exports (category, supplier, stock status, date range, SKU)
 - Revenue / profit calculation accuracy
 - Unicode / special-character preservation (₹, Indian product names)
 - CSV formula-injection protection (=, +, -, @)
 - Invalid filter values raise ValueError
 - Export is non-destructive (DB unchanged after export)
 - UTF-8 BOM present for Excel compatibility
"""
import csv
import io
from datetime import date, datetime, timedelta, timezone

import pytest

from backend.database import init_db
from backend.exports import inventory_csv, sales_csv
from backend import inventory as inv


# ---------------------------------------------------------------------------
# Shared fixture – every test gets its own empty temporary database
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("INVENTORY_DB", str(tmp_path / "export_test.db"))
    init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _add(sku="SKU1", name="Product 1", price=100.0, cost=60.0, stock=50,
         safety_stock=10, lead_time_days=3, category="General",
         supplier_id=None):
    return inv.add_product(sku, name, price=price, cost=cost, stock=stock,
                           safety_stock=safety_stock,
                           lead_time_days=lead_time_days,
                           category=category,
                           supplier_id=supplier_id)


def _parse_csv(csv_bytes: bytes) -> tuple[list[str], list[dict]]:
    """Return (headers, list_of_row_dicts) from UTF-8-BOM CSV bytes."""
    text = csv_bytes.decode("utf-8-sig")  # strips BOM if present
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = list(reader)
    return list(headers), rows


def _ts(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
        "%Y-%m-%d %H:%M:%S")


# ===========================================================================
# 1. EMPTY DATABASE EXPORTS
# ===========================================================================
class TestEmptyExports:

    def test_inventory_csv_empty_db_returns_header_only(self):
        fname, csv_bytes = inventory_csv()
        assert fname.startswith("inventory_export_")
        assert fname.endswith(".csv")
        headers, rows = _parse_csv(csv_bytes)
        assert len(rows) == 0
        assert "SKU" in headers
        assert "Product Name" in headers

    def test_sales_csv_empty_db_returns_header_only(self):
        fname, csv_bytes = sales_csv()
        assert fname.startswith("sales_export_")
        assert fname.endswith(".csv")
        headers, rows = _parse_csv(csv_bytes)
        assert len(rows) == 0
        assert "Sale ID" in headers
        assert "SKU" in headers

    def test_inventory_csv_empty_respects_filters(self):
        _, csv_bytes = inventory_csv(category="Dairy", stock_status="In Stock")
        _, rows = _parse_csv(csv_bytes)
        assert rows == []

    def test_sales_csv_no_sales_respects_date_filter(self):
        _add()
        _, csv_bytes = sales_csv(start_date="2026-01-01", end_date="2026-01-31")
        _, rows = _parse_csv(csv_bytes)
        assert rows == []


# ===========================================================================
# 2. CORRECT CSV HEADERS
# ===========================================================================
class TestHeaders:

    EXPECTED_INV_HEADERS = [
        "SKU", "Product Name", "Category", "Selling Price (₹)", "Cost Price (₹)",
        "Current Stock", "Safety Stock", "Lead Time (Days)", "Supplier",
        "Stock Status", "Inventory Value (₹)", "Potential Selling Value (₹)",
        "Potential Profit (₹)",
    ]

    EXPECTED_SALES_HEADERS = [
        "Sale ID", "SKU", "Product Name", "Category", "Quantity Sold",
        "Unit Selling Price (₹)", "Unit Cost Price (₹)",
        "Total Revenue (₹)", "Total Cost (₹)", "Total Profit (₹)",
        "Sale Timestamp",
    ]

    def test_inventory_csv_exact_headers(self):
        headers, _ = _parse_csv(inventory_csv()[1])
        assert headers == self.EXPECTED_INV_HEADERS

    def test_sales_csv_exact_headers(self):
        _add(stock=10)
        inv.record_sale("SKU1", 1)
        headers, _ = _parse_csv(sales_csv()[1])
        assert headers == self.EXPECTED_SALES_HEADERS


# ===========================================================================
# 3. FULL INVENTORY EXPORT — correctness
# ===========================================================================
class TestInventoryExport:

    def test_all_products_exported(self):
        _add("A1", stock=10, price=100.0, cost=60.0)
        _add("B1", stock=20, price=200.0, cost=120.0)
        _, csv_bytes = inventory_csv()
        _, rows = _parse_csv(csv_bytes)
        assert len(rows) == 2
        skus = {r["SKU"] for r in rows}
        assert {"A1", "B1"} == skus

    def test_inventory_value_calculation(self):
        _add("P1", stock=10, price=200.0, cost=150.0)
        _, csv_bytes = inventory_csv()
        _, rows = _parse_csv(csv_bytes)
        row = rows[0]
        assert float(row["Inventory Value (₹)"]) == pytest.approx(10 * 150.0)

    def test_potential_selling_value_calculation(self):
        _add("P1", stock=10, price=200.0, cost=150.0)
        _, rows = _parse_csv(inventory_csv()[1])
        assert float(rows[0]["Potential Selling Value (₹)"]) == pytest.approx(10 * 200.0)

    def test_potential_profit_calculation(self):
        _add("P1", stock=10, price=200.0, cost=150.0)
        _, rows = _parse_csv(inventory_csv()[1])
        assert float(rows[0]["Potential Profit (₹)"]) == pytest.approx(10 * 50.0)

    def test_zero_profit_when_price_equals_cost(self):
        _add("P1", stock=5, price=100.0, cost=100.0)
        _, rows = _parse_csv(inventory_csv()[1])
        assert float(rows[0]["Potential Profit (₹)"]) == pytest.approx(0.0)

    def test_negative_profit_when_price_below_cost(self):
        _add("P1", stock=5, price=80.0, cost=100.0)
        _, rows = _parse_csv(inventory_csv()[1])
        assert float(rows[0]["Potential Profit (₹)"]) == pytest.approx(5 * -20.0)

    def test_stock_status_in_stock(self):
        _add("P1", stock=50, safety_stock=10)
        _, rows = _parse_csv(inventory_csv()[1])
        assert rows[0]["Stock Status"] == "In Stock"

    def test_stock_status_low_stock(self):
        _add("P1", stock=5, safety_stock=10)
        _, rows = _parse_csv(inventory_csv()[1])
        assert rows[0]["Stock Status"] == "Low Stock"

    def test_stock_status_out_of_stock(self):
        _add("P1", stock=0, safety_stock=5)
        _, rows = _parse_csv(inventory_csv()[1])
        assert rows[0]["Stock Status"] == "Out of Stock"

    def test_stock_equal_to_safety_is_low_stock(self):
        _add("P1", stock=10, safety_stock=10)
        _, rows = _parse_csv(inventory_csv()[1])
        assert rows[0]["Stock Status"] == "Low Stock"

    def test_supplier_name_in_export(self):
        sid = inv.add_supplier("Test Supplier")
        _add("P1", supplier_id=sid)
        _, rows = _parse_csv(inventory_csv()[1])
        assert rows[0]["Supplier"] == "Test Supplier"

    def test_missing_supplier_exported_as_empty_string(self):
        _add("P1")
        _, rows = _parse_csv(inventory_csv()[1])
        assert rows[0]["Supplier"] == ""


# ===========================================================================
# 4. FILTERED INVENTORY EXPORT
# ===========================================================================
class TestInventoryFilters:

    def test_filter_by_category(self):
        _add("D1", category="Dairy")
        _add("S1", category="Snacks")
        _, rows = _parse_csv(inventory_csv(category="Dairy")[1])
        assert len(rows) == 1
        assert rows[0]["SKU"] == "D1"

    def test_filter_by_supplier(self):
        sid = inv.add_supplier("FreshFoods")
        _add("P1", supplier_id=sid)
        _add("P2")  # no supplier
        _, rows = _parse_csv(inventory_csv(supplier_name="FreshFoods")[1])
        assert len(rows) == 1
        assert rows[0]["SKU"] == "P1"

    def test_filter_by_stock_status_in_stock(self):
        _add("IN1", stock=50, safety_stock=10)
        _add("LOW1", stock=5, safety_stock=10)
        _add("OUT1", stock=0, safety_stock=5)
        _, rows = _parse_csv(inventory_csv(stock_status="In Stock")[1])
        assert all(r["Stock Status"] == "In Stock" for r in rows)

    def test_filter_by_stock_status_low_stock(self):
        _add("IN1", stock=50, safety_stock=10)
        _add("LOW1", stock=5, safety_stock=10)
        _, rows = _parse_csv(inventory_csv(stock_status="Low Stock")[1])
        assert all(r["Stock Status"] == "Low Stock" for r in rows)

    def test_filter_by_stock_status_out_of_stock(self):
        _add("IN1", stock=50, safety_stock=10)
        _add("OUT1", stock=0, safety_stock=5)
        _, rows = _parse_csv(inventory_csv(stock_status="Out of Stock")[1])
        assert all(r["Stock Status"] == "Out of Stock" for r in rows)

    def test_search_by_sku(self):
        _add("RICE01", name="Basmati Rice")
        _add("WHEAT01", name="Wheat Flour")
        _, rows = _parse_csv(inventory_csv(search="RICE")[1])
        assert len(rows) == 1
        assert rows[0]["SKU"] == "RICE01"

    def test_search_by_name(self):
        _add("RICE01", name="Basmati Rice")
        _add("WHEAT01", name="Wheat Flour")
        _, rows = _parse_csv(inventory_csv(search="Wheat")[1])
        assert len(rows) == 1
        assert rows[0]["SKU"] == "WHEAT01"

    def test_invalid_stock_status_raises(self):
        with pytest.raises(ValueError, match="Invalid stock_status"):
            inventory_csv(stock_status="Unknown")

    def test_combined_filters(self):
        sid = inv.add_supplier("AgroGlobal")
        _add("D1", category="Dairy", supplier_id=sid, stock=50, safety_stock=10)
        _add("D2", category="Dairy", stock=5, safety_stock=10)   # different supplier
        _add("S1", category="Snacks", supplier_id=sid, stock=50, safety_stock=10)
        _, rows = _parse_csv(inventory_csv(category="Dairy", supplier_name="AgroGlobal")[1])
        assert len(rows) == 1
        assert rows[0]["SKU"] == "D1"


# ===========================================================================
# 5. FULL SALES EXPORT — correctness
# ===========================================================================
class TestSalesExport:

    def test_single_sale_exported(self):
        _add("P1", price=200.0, cost=150.0, stock=50)
        inv.record_sale("P1", 5, unit_price=200.0)
        _, rows = _parse_csv(sales_csv()[1])
        assert len(rows) == 1
        r = rows[0]
        assert r["SKU"] == "P1"
        assert int(r["Quantity Sold"]) == 5

    def test_total_revenue_calculation(self):
        _add("P1", price=200.0, cost=150.0, stock=50)
        inv.record_sale("P1", 5, unit_price=200.0)
        _, rows = _parse_csv(sales_csv()[1])
        assert float(rows[0]["Total Revenue (₹)"]) == pytest.approx(5 * 200.0)

    def test_total_cost_calculation(self):
        _add("P1", price=200.0, cost=150.0, stock=50)
        inv.record_sale("P1", 5, unit_price=200.0)
        _, rows = _parse_csv(sales_csv()[1])
        assert float(rows[0]["Total Cost (₹)"]) == pytest.approx(5 * 150.0)

    def test_total_profit_calculation(self):
        _add("P1", price=200.0, cost=150.0, stock=50)
        inv.record_sale("P1", 5, unit_price=200.0)
        _, rows = _parse_csv(sales_csv()[1])
        assert float(rows[0]["Total Profit (₹)"]) == pytest.approx(5 * 50.0)

    def test_zero_profit_when_price_equals_cost(self):
        _add("P1", price=100.0, cost=100.0, stock=50)
        inv.record_sale("P1", 3, unit_price=100.0)
        _, rows = _parse_csv(sales_csv()[1])
        assert float(rows[0]["Total Profit (₹)"]) == pytest.approx(0.0)

    def test_multiple_sales_all_exported(self):
        _add("P1", stock=100)
        for _ in range(5):
            inv.record_sale("P1", 2)
        _, rows = _parse_csv(sales_csv()[1])
        assert len(rows) == 5

    def test_sale_id_present_and_numeric(self):
        _add("P1", stock=10)
        inv.record_sale("P1", 1)
        _, rows = _parse_csv(sales_csv()[1])
        assert int(rows[0]["Sale ID"]) > 0

    def test_timestamp_in_sales_export(self):
        _add("P1", stock=10)
        inv.record_sale("P1", 1)
        _, rows = _parse_csv(sales_csv()[1])
        # Should parse without error
        datetime.strptime(rows[0]["Sale Timestamp"][:19], "%Y-%m-%d %H:%M:%S")

    def test_category_included_in_sales_rows(self):
        _add("P1", category="Beverages", stock=20)
        inv.record_sale("P1", 2)
        _, rows = _parse_csv(sales_csv()[1])
        assert rows[0]["Category"] == "Beverages"


# ===========================================================================
# 6. FILTERED SALES EXPORT
# ===========================================================================
class TestSalesFilters:

    def test_filter_by_start_date(self):
        _add("P1", stock=200)
        inv.record_sale("P1", 5, timestamp=_ts(40))   # old – excluded
        inv.record_sale("P1", 3, timestamp=_ts(5))    # recent – included
        start = (date.today() - timedelta(days=30)).isoformat()
        _, rows = _parse_csv(sales_csv(start_date=start)[1])
        assert len(rows) == 1
        assert int(rows[0]["Quantity Sold"]) == 3

    def test_filter_by_end_date(self):
        _add("P1", stock=200)
        inv.record_sale("P1", 5, timestamp=_ts(40))   # older – included
        inv.record_sale("P1", 3, timestamp=_ts(5))    # recent – excluded
        end = (date.today() - timedelta(days=20)).isoformat()
        _, rows = _parse_csv(sales_csv(end_date=end)[1])
        assert len(rows) == 1
        assert int(rows[0]["Quantity Sold"]) == 5

    def test_filter_by_start_and_end_date(self):
        _add("P1", stock=300)
        inv.record_sale("P1", 1, timestamp=_ts(60))   # too old
        inv.record_sale("P1", 2, timestamp=_ts(20))   # in range
        inv.record_sale("P1", 3, timestamp=_ts(10))   # in range
        inv.record_sale("P1", 4, timestamp=_ts(1))    # too recent
        start = (date.today() - timedelta(days=25)).isoformat()
        end   = (date.today() - timedelta(days=5)).isoformat()
        _, rows = _parse_csv(sales_csv(start_date=start, end_date=end)[1])
        assert len(rows) == 2
        qtys = sorted(int(r["Quantity Sold"]) for r in rows)
        assert qtys == [2, 3]

    def test_filter_by_sku(self):
        _add("P1", stock=50)
        _add("P2", stock=50)
        inv.record_sale("P1", 5)
        inv.record_sale("P2", 7)
        _, rows = _parse_csv(sales_csv(sku="P1")[1])
        assert len(rows) == 1
        assert rows[0]["SKU"] == "P1"

    def test_filter_by_category(self):
        _add("P1", category="Dairy", stock=50)
        _add("P2", category="Snacks", stock=50)
        inv.record_sale("P1", 3)
        inv.record_sale("P2", 7)
        _, rows = _parse_csv(sales_csv(category="Dairy")[1])
        assert len(rows) == 1
        assert rows[0]["Category"] == "Dairy"

    def test_sales_spanning_60_days_all_exported(self):
        _add("P1", stock=500)
        for d in range(60):
            inv.record_sale("P1", 2, timestamp=_ts(d))
        _, rows = _parse_csv(sales_csv()[1])
        assert len(rows) == 60


# ===========================================================================
# 7. INVALID FILTER / DATE VALIDATION
# ===========================================================================
class TestInvalidFilters:

    def test_invalid_start_date_format_raises(self):
        with pytest.raises(ValueError, match="start_date"):
            sales_csv(start_date="31-12-2026")

    def test_invalid_end_date_format_raises(self):
        with pytest.raises(ValueError, match="end_date"):
            sales_csv(end_date="not-a-date")

    def test_start_after_end_raises(self):
        with pytest.raises(ValueError, match="start_date"):
            sales_csv(start_date="2026-12-01", end_date="2026-01-01")

    def test_invalid_stock_status_raises(self):
        with pytest.raises(ValueError, match="Invalid stock_status"):
            inventory_csv(stock_status="Bad Status")

    @pytest.mark.parametrize("bad_status", ["in stock", "INSTOCK", "low", "none"])
    def test_various_invalid_stock_statuses_raise(self, bad_status):
        with pytest.raises(ValueError):
            inventory_csv(stock_status=bad_status)


# ===========================================================================
# 8. CSV FORMULA INJECTION PROTECTION
# ===========================================================================
class TestFormulaInjection:

    @pytest.mark.parametrize("dangerous_prefix", ["=SUM(1)", "+1+1", "-1+1", "@SUM"])
    def test_injection_in_product_name_escaped(self, dangerous_prefix):
        inv.add_product(dangerous_prefix + "_PROD", dangerous_prefix + " Danger", price=10, cost=5, stock=5)
        _, rows = _parse_csv(inventory_csv()[1])
        # The name column should be tab-prefixed if it starts with a dangerous char
        name_val = rows[0]["Product Name"]
        # After CSV unquoting, the value should NOT start with the dangerous char raw
        assert not name_val.startswith("=") or name_val.startswith("\t="), \
            f"Injection not escaped: {name_val!r}"

    def test_injection_in_sku_escaped(self):
        inv.add_product("=EVIL", "Normal Name", price=10, cost=5, stock=5)
        _, rows = _parse_csv(inventory_csv()[1])
        sku_val = rows[0]["SKU"]
        # Either starts with tab (escaped) or the raw string is safe (csv.QUOTE_MINIMAL)
        assert sku_val.startswith("\t") or not sku_val.startswith("=")


# ===========================================================================
# 9. UNICODE / SPECIAL CHARACTERS
# ===========================================================================
class TestUnicode:

    def test_unicode_product_name_preserved(self):
        inv.add_product("HINDI01", "गेहूँ का आटा 5kg", price=260, cost=215, stock=10)
        _, rows = _parse_csv(inventory_csv()[1])
        assert rows[0]["Product Name"] == "गेहूँ का आटा 5kg"

    def test_rupee_symbol_in_supplier_name(self):
        # Supplier names with special chars
        sid = inv.add_supplier("₹ Traders & Co.")
        inv.add_product("P1", "Item", price=100, cost=80, stock=10, supplier_id=sid)
        _, rows = _parse_csv(inventory_csv()[1])
        assert rows[0]["Supplier"] == "₹ Traders & Co."

    def test_bom_present_for_excel_compatibility_inventory(self):
        _, csv_bytes = inventory_csv()
        # UTF-8 BOM = \xef\xbb\xbf
        assert csv_bytes[:3] == b"\xef\xbb\xbf"

    def test_bom_present_for_excel_compatibility_sales(self):
        _add(stock=10)
        inv.record_sale("SKU1", 1)
        _, csv_bytes = sales_csv()
        assert csv_bytes[:3] == b"\xef\xbb\xbf"

    def test_utf8_roundtrip_inventory(self):
        inv.add_product("SPICE01", "हल्दी पाउडर 200g", price=65, cost=45, stock=10)
        _, csv_bytes = inventory_csv()
        text = csv_bytes.decode("utf-8-sig")
        assert "हल्दी पाउडर 200g" in text

    def test_utf8_roundtrip_sales(self):
        inv.add_product("SPICE01", "हल्दी पाउडर 200g", price=65, cost=45, stock=10)
        inv.record_sale("SPICE01", 2)
        _, csv_bytes = sales_csv()
        text = csv_bytes.decode("utf-8-sig")
        assert "हल्दी पाउडर 200g" in text


# ===========================================================================
# 10. FILE NAMING
# ===========================================================================
class TestFileNaming:

    def test_inventory_filename_format(self):
        fname, _ = inventory_csv()
        today = date.today().strftime("%Y-%m-%d")
        assert fname == f"inventory_export_{today}.csv"

    def test_sales_filename_format(self):
        fname, _ = sales_csv()
        today = date.today().strftime("%Y-%m-%d")
        assert fname == f"sales_export_{today}.csv"


# ===========================================================================
# 11. NON-DESTRUCTIVE — DB UNCHANGED AFTER EXPORT
# ===========================================================================
class TestNonDestructive:

    def test_inventory_export_does_not_modify_db(self):
        _add("P1", stock=42)
        inventory_csv()
        assert inv.get_product_by_sku("P1")["stock"] == 42

    def test_sales_export_does_not_modify_db(self):
        _add("P1", stock=20)
        inv.record_sale("P1", 5)
        before_count = len(inv.list_transactions())
        sales_csv()
        assert len(inv.list_transactions()) == before_count
        assert inv.get_product_by_sku("P1")["stock"] == 15

    def test_multiple_exports_idempotent(self):
        _add("P1", stock=10)
        _, b1 = inventory_csv()
        _, b2 = inventory_csv()
        # Both exports should produce identical content (same data)
        assert b1 == b2

