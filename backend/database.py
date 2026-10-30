"""SQLite connection and schema for the Smart Inventory Management System."""
import os
import sqlite3

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "inventory.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'staff'))
);

CREATE TABLE IF NOT EXISTS suppliers (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE,
    phone TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    sku            TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    category       TEXT,
    price          REAL NOT NULL CHECK (price >= 0),
    cost           REAL NOT NULL DEFAULT 0 CHECK (cost >= 0),
    stock          INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    lead_time_days INTEGER NOT NULL DEFAULT 3 CHECK (lead_time_days >= 0),
    safety_stock   INTEGER NOT NULL DEFAULT 0 CHECK (safety_stock >= 0),
    supplier_id    INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    type       TEXT NOT NULL CHECK (type IN ('SALE', 'PURCHASE')),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    timestamp  TEXT NOT NULL DEFAULT (datetime('now')),
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tx_product_time ON transactions(product_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_tx_type_time ON transactions(type, timestamp);
"""


def get_db_path():
    """Database file location; override with the INVENTORY_DB env var (used by tests)."""
    return os.environ.get("INVENTORY_DB", DEFAULT_DB_PATH)


def get_connection():
    """Open a connection with row access by column name and foreign keys enforced."""
    path = get_db_path()
    if path != ":memory:":
        os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables and indexes if they do not exist yet."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def query(sql, params=()):
    """Run a SELECT and return all rows as a list of dicts."""
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
