import pytest

from backend import auth, inventory as inv


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("INVENTORY_DB", str(tmp_path / "test.db"))


@pytest.fixture
def rice():
    inv.add_product("rice01", "Basmati Rice 5kg", price=500, cost=400, stock=100)
    return "RICE01"


def test_add_product_normalizes_sku_and_lookup(rice):
    assert inv.get_product_by_sku("rice01")["name"] == "Basmati Rice 5kg"
    assert "RICE01" in inv.build_sku_index()


def test_duplicate_sku_rejected(rice):
    with pytest.raises(inv.DuplicateError):
        inv.add_product("RICE01", "Other", price=1)


def test_unknown_sku_raises():
    inv.add_product("A1", "A", price=1)
    with pytest.raises(inv.ProductNotFoundError):
        inv.get_product_by_sku("NOPE")


def test_sale_decreases_stock_and_logs(rice):
    inv.record_sale(rice, 30)
    assert inv.get_product_by_sku(rice)["stock"] == 70
    tx = inv.list_transactions(sku=rice)[0]
    assert (tx["type"], tx["quantity"], tx["unit_price"]) == ("SALE", 30, 500)


def test_purchase_increases_stock(rice):
    inv.record_purchase(rice, 50)
    assert inv.get_product_by_sku(rice)["stock"] == 150


def test_cannot_oversell_and_nothing_is_logged(rice):
    with pytest.raises(inv.InsufficientStockError):
        inv.record_sale(rice, 101)
    assert inv.get_product_by_sku(rice)["stock"] == 100
    assert inv.list_transactions(sku=rice) == []


@pytest.mark.parametrize("qty", [0, -5, 2.5, "3"])
def test_invalid_quantity_rejected(rice, qty):
    with pytest.raises(inv.InventoryError):
        inv.record_sale(rice, qty)


def test_update_product_blocks_direct_stock_edit(rice):
    inv.update_product(rice, price=550)
    assert inv.get_product_by_sku(rice)["price"] == 550
    with pytest.raises(inv.InventoryError):
        inv.update_product(rice, stock=999)


def test_delete_product_removes_its_history(rice):
    inv.record_sale(rice, 1)
    inv.delete_product(rice)
    assert inv.list_products() == []
    assert inv.list_transactions() == []


def test_deleting_supplier_keeps_product():
    sid = inv.add_supplier("Agro Co")
    inv.add_product("A1", "A", price=1, supplier_id=sid)
    inv.delete_supplier(sid)
    assert inv.get_product_by_sku("A1")["supplier_id"] is None


def test_search_and_filter():
    inv.add_product("A1", "Apple", price=1, category="Fruit")
    inv.add_product("B1", "Bread", price=1, category="Bakery")
    assert [p["sku"] for p in inv.list_products(search="app")] == ["A1"]
    assert [p["sku"] for p in inv.list_products(category="Bakery")] == ["B1"]


def test_dashboard_summary(rice):
    inv.record_sale(rice, 2)
    s = inv.dashboard_summary()
    assert s["total_products"] == 1
    assert s["stock_value"] == 98 * 400
    assert s["today_sales"] == 1000


def test_auth_roundtrip():
    auth.create_user("bob", "pw123", "staff")
    assert auth.authenticate("bob", "pw123")["role"] == "staff"
    assert auth.authenticate("bob", "wrong") is None
    assert auth.authenticate("ghost", "pw123") is None
    with pytest.raises(ValueError):
        auth.create_user("bob", "x")
