"""CSV export backend (Person 4).

Provides two pure-Python functions that return an (filename, csv_bytes) tuple:
  - inventory_csv(...)  – filtered inventory snapshot with valuations
  - sales_csv(...)      – filtered sales transactions with profit figures

Design goals
~~~~~~~~~~~~
* No SQL in this module – delegates entirely to backend.inventory helpers.
* Formula-injection protection: cells starting with = + - @ are prefixed with
  a tab character so spreadsheet software treats them as text.
* UTF-8 BOM (\\ufeff) prepended so Excel opens the file without encoding issues
  and renders the ₹ symbol correctly.
* Handles empty datasets gracefully (header-only CSV is returned).
* All filter parameters are validated; invalid values raise ValueError.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone

from backend.inventory import list_products, list_transactions, list_suppliers


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_INJECT_CHARS = {"=", "+", "-", "@", "\t", "\r"}


def _safe_cell(value: object) -> str:
    """Escape CSV formula-injection: prefix dangerous leading chars with TAB."""
    text = str(value) if value is not None else ""
    if text and text[0] in _INJECT_CHARS:
        return "\t" + text
    return text


def _stock_status(stock: int, safety: int) -> str:
    if stock == 0:
        return "Out of Stock"
    if stock <= safety:
        return "Low Stock"
    return "In Stock"


def _build_csv(headers: list[str], rows: list[list]) -> bytes:
    """Render headers + rows to UTF-8 BOM bytes."""
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_safe_cell(cell) for cell in row])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


# ---------------------------------------------------------------------------
# Inventory CSV
# ---------------------------------------------------------------------------
_INV_HEADERS = [
    "SKU", "Product Name", "Category", "Selling Price (₹)", "Cost Price (₹)",
    "Current Stock", "Safety Stock", "Lead Time (Days)", "Supplier",
    "Stock Status", "Inventory Value (₹)", "Potential Selling Value (₹)",
    "Potential Profit (₹)",
]


def inventory_csv(
    *,
    search: str | None = None,
    category: str | None = None,
    supplier_name: str | None = None,
    stock_status: str | None = None,          # "In Stock" | "Low Stock" | "Out of Stock" | None
    as_of: date | None = None,                # reserved for future time-travel; unused today
) -> tuple[str, bytes]:
    """Return (filename, csv_bytes) for the filtered inventory snapshot.

    Parameters
    ----------
    search        – free-text search passed to inv.list_products()
    category      – exact category name filter
    supplier_name – filter by supplier display name (case-insensitive)
    stock_status  – one of "In Stock", "Low Stock", "Out of Stock", or None for all
    as_of         – reserved; not used yet
    """
    valid_statuses = {None, "In Stock", "Low Stock", "Out of Stock"}
    if stock_status not in valid_statuses:
        raise ValueError(
            f"Invalid stock_status '{stock_status}'. "
            f"Must be one of: {sorted(s for s in valid_statuses if s)}."
        )

    # Fetch products with backend search + category filters
    products = list_products(
        search=search.strip() if search else None,
        category=category.strip() if category else None,
    )

    # Apply supplier name filter (client-side; supplier_name is a display field)
    if supplier_name:
        norm = supplier_name.strip().lower()
        products = [
            p for p in products
            if (p.get("supplier_name") or "").lower() == norm
        ]

    # Apply stock status filter
    if stock_status:
        products = [
            p for p in products
            if _stock_status(p.get("stock", 0), p.get("safety_stock") or 0) == stock_status
        ]

    rows: list[list] = []
    for p in products:
        stock   = p.get("stock", 0)
        cost    = float(p.get("cost") or 0.0)
        price   = float(p.get("price") or 0.0)
        safety  = int(p.get("safety_stock") or 0)
        inv_val = round(stock * cost, 2)
        sell_val = round(stock * price, 2)
        profit   = round(stock * (price - cost), 2)
        rows.append([
            p["sku"],
            p["name"],
            p.get("category") or "",
            round(price, 2),
            round(cost, 2),
            stock,
            safety,
            p.get("lead_time_days", 3),
            p.get("supplier_name") or "",
            _stock_status(stock, safety),
            inv_val,
            sell_val,
            profit,
        ])

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"inventory_export_{today_str}.csv"
    return filename, _build_csv(_INV_HEADERS, rows)


# ---------------------------------------------------------------------------
# Sales CSV
# ---------------------------------------------------------------------------
_SALES_HEADERS = [
    "Sale ID", "SKU", "Product Name", "Category", "Quantity Sold",
    "Unit Selling Price (₹)", "Unit Cost Price (₹)",
    "Total Revenue (₹)", "Total Cost (₹)", "Total Profit (₹)",
    "Sale Timestamp",
]


def sales_csv(
    *,
    start_date: date | str | None = None,
    end_date:   date | str | None = None,
    sku:        str | None = None,
    category:   str | None = None,
) -> tuple[str, bytes]:
    """Return (filename, csv_bytes) for the filtered sales transaction log.

    Parameters
    ----------
    start_date – inclusive lower bound (date or 'YYYY-MM-DD' string)
    end_date   – inclusive upper bound (date or 'YYYY-MM-DD' string)
    sku        – filter to a single product SKU
    category   – filter by product category (requires cross-referencing products)
    """
    # ── Date validation ───────────────────────────────────────────────────────
    def _parse(d: date | str | None, name: str) -> date | None:
        if d is None:
            return None
        if isinstance(d, date):
            return d
        try:
            return datetime.strptime(str(d).strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(
                f"Invalid {name} '{d}'. Expected format: YYYY-MM-DD."
            )

    start = _parse(start_date, "start_date")
    end   = _parse(end_date,   "end_date")

    if start and end and start > end:
        raise ValueError(
            f"start_date ({start}) must not be after end_date ({end})."
        )

    # Convert start/end to since-timestamp string for the backend
    since_ts: str | None = None
    if start:
        since_ts = f"{start.strftime('%Y-%m-%d')} 00:00:00"

    transactions = list_transactions(
        sku=sku.strip().upper() if sku else None,
        tx_type="SALE",
        since=since_ts,
    )

    # Apply end-date filter (backend has no "until" param)
    if end:
        end_str = f"{end.strftime('%Y-%m-%d')} 23:59:59"
        transactions = [t for t in transactions if t["timestamp"] <= end_str]

    # Build product lookup for category filter + cost price enrichment
    # (transactions don't store unit_cost, so we look it up from the catalog)
    if category:
        cat_norm = category.strip().lower()
        products_by_sku = {p["sku"]: p for p in list_products()}
        transactions = [
            t for t in transactions
            if (products_by_sku.get(t["sku"], {}).get("category") or "").lower() == cat_norm
        ]
        # (reuse for cost below)
    else:
        products_by_sku = {p["sku"]: p for p in list_products()}

    rows: list[list] = []
    for t in transactions:
        qty        = t["quantity"]
        unit_price = float(t["unit_price"])
        unit_cost  = float(products_by_sku.get(t["sku"], {}).get("cost") or 0.0)
        revenue    = round(qty * unit_price, 2)
        cost_total = round(qty * unit_cost, 2)
        profit     = round(revenue - cost_total, 2)
        prod       = products_by_sku.get(t["sku"], {})
        rows.append([
            t["id"],
            t["sku"],
            t.get("product_name") or prod.get("name") or t["sku"],
            prod.get("category") or "",
            qty,
            round(unit_price, 2),
            round(unit_cost, 2),
            revenue,
            cost_total,
            profit,
            t["timestamp"],
        ])

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"sales_export_{today_str}.csv"
    return filename, _build_csv(_SALES_HEADERS, rows)

