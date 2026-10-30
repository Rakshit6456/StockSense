"""Core inventory logic: suppliers, products, sales and purchases."""
import sqlite3

from backend.database import get_connection, init_db, query

class InventoryError(Exception):
    """Base class for all inventory errors."""

class ProductNotFoundError(InventoryError):
    pass
class InsufficientStockError(InventoryError):
    pass
class DuplicateError(InventoryError):
    pass
# ---------- suppliers ----------
def add_supplier(name, phone=None, email=None):
    init_db()
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO suppliers (name, phone, email) VALUES (?, ?, ?)",
                (name.strip(), phone, email),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise DuplicateError(f"Supplier '{name}' already exists")


def list_suppliers():
    return query("SELECT * FROM suppliers ORDER BY name")


def update_supplier(supplier_id, name, phone=None, email=None):
    with get_connection() as conn:
        conn.execute(
            "UPDATE suppliers SET name = ?, phone = ?, email = ? WHERE id = ?",
            (name.strip(), phone, email, supplier_id),
        )
def delete_supplier(supplier_id):
    """Products keep existing; their supplier_id becomes NULL."""
    with get_connection() as conn:
        conn.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))

# ---------- products ----------
def add_product(sku, name, price, category=None, cost=0.0, stock=0,
                lead_time_days=3, safety_stock=0, supplier_id=None):
    init_db()
    sku = sku.strip().upper()
    if not sku or not name.strip():
        raise InventoryError("SKU and name are required")
    try:
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO products
                   (sku, name, category, price, cost, stock, lead_time_days,
                    safety_stock, supplier_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sku, name.strip(), category, price, cost, stock,
                 lead_time_days, safety_stock, supplier_id),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e):
            raise DuplicateError(f"SKU '{sku}' already exists")
        raise InventoryError(f"Invalid product data: {e}")

def get_product_by_sku(sku):
    rows = query("SELECT * FROM products WHERE sku = ?", (sku.strip().upper(),))
    if not rows:
        raise ProductNotFoundError(f"No product with SKU '{sku}'")
    return rows[0]

def build_sku_index():
    """Hash map (dict) of SKU -> product row, for O(1) lookups in the UI/billing flow."""
    return {p["sku"]: p for p in list_products()}

def list_products(search=None, category=None):
    sql = """SELECT p.*, s.name AS supplier_name
             FROM products p LEFT JOIN suppliers s ON s.id = p.supplier_id
             WHERE 1=1"""
    params = []
    if search:
        sql += " AND (p.sku LIKE ? OR p.name LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if category:
        sql += " AND p.category = ?"
        params.append(category)
    return query(sql + " ORDER BY p.name", params)

def update_product(sku, **fields):
    """Update any of: name, category, price, cost, lead_time_days, safety_stock, supplier_id.
    Stock is changed only through sales/purchases so history stays consistent."""
    allowed = {"name", "category", "price", "cost", "lead_time_days",
               "safety_stock", "supplier_id"}
    bad = set(fields) - allowed
    if bad:
        raise InventoryError(f"Cannot update fields: {', '.join(sorted(bad))}")
    if not fields:
        return
    product = get_product_by_sku(sku)
    assignments = ", ".join(f"{k} = ?" for k in fields)
    try:
        with get_connection() as conn:
            conn.execute(f"UPDATE products SET {assignments} WHERE id = ?",
                         (*fields.values(), product["id"]))
    except sqlite3.IntegrityError as e:
        raise InventoryError(f"Invalid product data: {e}")

def delete_product(sku):
    product = get_product_by_sku(sku)
    with get_connection() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product["id"],))

# ---------- transactions ----------
def _record(sku, qty, tx_type, unit_price=None, user_id=None, timestamp=None):
    if not isinstance(qty, int) or qty <= 0:
        raise InventoryError("Quantity must be a positive whole number")
    product = get_product_by_sku(sku)
    if unit_price is None:
        unit_price = product["price"] if tx_type == "SALE" else product["cost"]
    delta = -qty if tx_type == "SALE" else qty

    conn = get_connection()
    try:
        with conn:  # one atomic transaction: stock update + history row
            if tx_type == "SALE":
                # Guarded update so two concurrent sales can never push stock below 0.
                cur = conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                    (qty, product["id"], qty),
                )
                if cur.rowcount == 0:
                    raise InsufficientStockError(
                        f"Only {product['stock']} units of {product['sku']} in stock, "
                        f"cannot sell {qty}")
            else:
                conn.execute("UPDATE products SET stock = stock + ? WHERE id = ?",
                             (qty, product["id"]))
            if timestamp:
                cur = conn.execute(
                    """INSERT INTO transactions
                       (product_id, type, quantity, unit_price, user_id, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (product["id"], tx_type, qty, unit_price, user_id, timestamp))
            else:
                cur = conn.execute(
                    """INSERT INTO transactions
                       (product_id, type, quantity, unit_price, user_id)
                       VALUES (?, ?, ?, ?, ?)""",
                    (product["id"], tx_type, qty, unit_price, user_id))
            return cur.lastrowid
    finally:
        conn.close()
def record_sale(sku, qty, unit_price=None, user_id=None, timestamp=None):
    """Sell qty units: decreases stock. Raises InsufficientStockError if not enough.
    `timestamp` ('YYYY-MM-DD HH:MM:SS') is optional, for loading historical data."""
    return _record(sku, qty, "SALE", unit_price, user_id, timestamp)
def record_purchase(sku, qty, unit_cost=None, user_id=None, timestamp=None):
    """Receive qty units from a supplier: increases stock."""
    return _record(sku, qty, "PURCHASE", unit_cost, user_id, timestamp)
def list_transactions(sku=None, tx_type=None, since=None, limit=None):
    sql = """SELECT t.*, p.sku, p.name AS product_name
             FROM transactions t JOIN products p ON p.id = t.product_id
             WHERE 1=1"""
    params = []
    if sku:
        sql += " AND p.sku = ?"
        params.append(sku.strip().upper())
    if tx_type:
        sql += " AND t.type = ?"
        params.append(tx_type)
    if since:
        sql += " AND t.timestamp >= ?"
        params.append(since)
    sql += " ORDER BY t.timestamp DESC, t.id DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return query(sql, params)
def dashboard_summary():
    """Headline numbers for the dashboard cards."""
    row = query("""SELECT COUNT(*) AS total_products,
                          COALESCE(SUM(stock * cost), 0) AS stock_value
                   FROM products""")[0]
    sales = query("""SELECT COALESCE(SUM(quantity * unit_price), 0) AS today_sales
                     FROM transactions
                     WHERE type = 'SALE' AND date(timestamp) = date('now')""")[0]
    return {**row, **sales}
