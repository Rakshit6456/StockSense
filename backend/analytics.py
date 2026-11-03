"""Analytics engine (Person 2).

Provides sales velocity, inventory reorder calculations, ABC classification,
dead stock reporting, and time-series moving averages.
"""
from datetime import datetime, timedelta, timezone
import heapq
import math

from backend.database import init_db
from backend import inventory as inv


def average_daily_sales(sku: str, days: int = 30) -> float:
    """Average units sold per day over the last `days` days.

    Includes zero-sale days in the lookback window. Uses only SALE transactions.
    Returns 0.0 if days <= 0 or if no sales occurred.
    """
    init_db()
    if not sku or days <= 0:
        return 0.0

    sku = sku.strip().upper()
    # Verify product exists (raises ProductNotFoundError if unknown)
    inv.get_product_by_sku(sku)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    sales = inv.list_transactions(sku=sku, tx_type="SALE", since=cutoff)
    total_units_sold = sum(t["quantity"] for t in sales)
    return float(total_units_sold) / float(days)


def calculate_reorder_point(sku: str) -> int:
    """Calculate the inventory reorder point for a product.

    Formula: (average_daily_sales * lead_time_days) + safety_stock
    Average daily sales is kept as a full-precision float and the final
    result is rounded UP to the nearest integer using math.ceil.
    """
    init_db()
    sku = sku.strip().upper()
    product = inv.get_product_by_sku(sku)

    lead_time_days = product.get("lead_time_days")
    if lead_time_days is None:
        lead_time_days = 3

    safety_stock = product.get("safety_stock")
    if safety_stock is None:
        safety_stock = 0

    daily_sales = average_daily_sales(sku, days=30)
    rop = math.ceil((daily_sales * lead_time_days) + safety_stock)
    return int(rop)


def get_reorder_list() -> list[dict]:
    """Identify products where current stock < reorder point.

    Prioritizes items by largest stock shortage using a priority queue (heapq).
    Uses the documented Min-Max / Order-Up-To replenishment policy:
        target_stock = max(2 * reorder_point, safety_stock + 10)
        suggested_order_qty = max(reorder_point - stock, target_stock - stock)
    """
    init_db()
    products = inv.list_products()
    heap: list[tuple[int, str, dict]] = []

    for product in products:
        sku = product["sku"]
        stock = product.get("stock", 0)
        rop = calculate_reorder_point(sku)

        if stock < rop:
            shortage = rop - stock
            safety = product.get("safety_stock") or 0
            target_stock = max(2 * rop, safety + 10)
            suggested_order_qty = max(shortage, target_stock - stock)

            item = {
                "sku": sku,
                "name": product["name"],
                "category": product.get("category") or "General",
                "stock": stock,
                "reorder_point": rop,
                "suggested_order_qty": suggested_order_qty,
                "supplier_name": product.get("supplier_name") or "None",
            }
            # Min-heap ordered by -shortage to prioritize largest shortage first
            heapq.heappush(heap, (-shortage, sku, item))

    reorder_list = []
    while heap:
        reorder_list.append(heapq.heappop(heap)[2])

    return reorder_list


def abc_analysis() -> list[dict]:
    """Pareto ABC revenue analysis across all inventory products.

    Ranks products by total sales revenue descending:
    - Class A: Top revenue items accounting for up to 80% cumulative revenue.
    - Class B: Next tier accounting for up to 95% cumulative revenue.
    - Class C: Bottom tier accounting for the remaining >95% (or 0 revenue).

    Safely handles zero total revenue by classifying all products as Class C.
    """
    init_db()
    products = inv.list_products()
    if not products:
        return []

    # Map all products to ensure catalog-wide coverage
    names_by_sku = {p["sku"]: p["name"] for p in products}
    rev_by_sku = {p["sku"]: 0.0 for p in products}

    sales = inv.list_transactions(tx_type="SALE")
    for s in sales:
        sku = s["sku"]
        rev = s["quantity"] * s["unit_price"]
        if sku in rev_by_sku:
            rev_by_sku[sku] += rev
        else:
            rev_by_sku[sku] = rev
            names_by_sku[sku] = s.get("product_name", sku)

    total_revenue = sum(rev_by_sku.values())
    sorted_skus = sorted(
        rev_by_sku.keys(),
        key=lambda k: (rev_by_sku[k], names_by_sku.get(k, k)),
        reverse=True,
    )

    result = []
    cumulative = 0.0

    for sku in sorted_skus:
        revenue = rev_by_sku[sku]
        cumulative += revenue
        cum_pct = (cumulative / total_revenue * 100.0) if total_revenue > 0 else 0.0

        if total_revenue <= 0 or revenue <= 0:
            abc_class = "C"
        elif cum_pct <= 80.0 or len(result) == 0:
            abc_class = "A"
        elif cum_pct <= 95.0 or all(r["abc_class"] == "A" for r in result):
            abc_class = "B"
        else:
            abc_class = "C"

        result.append({
            "sku": sku,
            "name": names_by_sku.get(sku, sku),
            "revenue": round(revenue, 2),
            "cumulative_pct": round(cum_pct, 1),
            "abc_class": abc_class,
        })

    return result


def dead_stock(days: int = 30) -> list[dict]:
    """Identify products with positive stock that have no sales in the last `days` days.

    Returns a list of dicts sorted descending by capital_tied_up.
    """
    init_db()
    products = inv.list_products()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    dead = []
    for product in products:
        stock = product.get("stock", 0)
        if stock <= 0:
            continue

        sku = product["sku"]
        recent_sales = inv.list_transactions(sku=sku, tx_type="SALE", since=cutoff, limit=1)
        if not recent_sales:
            all_sales = inv.list_transactions(sku=sku, tx_type="SALE", limit=1)
            last_sale = all_sales[0]["timestamp"][:10] if all_sales else "Never"
            cost = float(product.get("cost") or 0.0)
            capital_tied_up = round(stock * cost, 2)

            dead.append({
                "sku": sku,
                "name": product["name"],
                "category": product.get("category") or "General",
                "stock": stock,
                "cost": cost,
                "capital_tied_up": capital_tied_up,
                "last_sale": last_sale,
            })

    dead.sort(key=lambda x: x["capital_tied_up"], reverse=True)
    return dead


def moving_average(sku: str, window: int = 7) -> list[dict]:
    """Calculate rolling moving average of daily sales for a product.

    Includes zero-sale days between the first and last sale dates.
    Returns a list of dicts with keys: date, units_sold, revenue, moving_avg.
    """
    init_db()
    if not sku:
        return []

    sku = sku.strip().upper()
    sales = inv.list_transactions(sku=sku, tx_type="SALE")
    if not sales:
        return []

    if window <= 0:
        window = 7

    # Aggregate units and revenue by calendar day (YYYY-MM-DD)
    daily: dict[str, dict[str, float]] = {}
    for s in sales:
        dt = s["timestamp"][:10]
        if dt not in daily:
            daily[dt] = {"units_sold": 0, "revenue": 0.0}
        daily[dt]["units_sold"] += s["quantity"]
        daily[dt]["revenue"] += s["quantity"] * s["unit_price"]

    all_dates = list(daily.keys())
    start_dt = datetime.strptime(min(all_dates), "%Y-%m-%d").date()
    end_dt = datetime.strptime(max(all_dates), "%Y-%m-%d").date()

    result = []
    recent_units: list[int] = []
    cur_dt = start_dt

    while cur_dt <= end_dt:
        dt_str = cur_dt.strftime("%Y-%m-%d")
        day_data = daily.get(dt_str, {"units_sold": 0, "revenue": 0.0})
        units = int(day_data["units_sold"])
        rev = float(day_data["revenue"])

        recent_units.append(units)
        if len(recent_units) > window:
            recent_units.pop(0)

        m_avg = round(sum(recent_units) / len(recent_units), 2)
        result.append({
            "date": dt_str,
            "units_sold": units,
            "revenue": round(rev, 2),
            "moving_avg": m_avg,
        })
        cur_dt += timedelta(days=1)

    return result
