"""Analytics engine (Person 2). Function signatures are fixed so the UI can call them now.

Data comes from backend.inventory (list_products, list_transactions) or backend.database.query.
"""


def average_daily_sales(sku, days=30):
    """Average units sold per day over the last `days` days."""
    raise NotImplementedError


def calculate_reorder_point(sku):
    """average daily sales * lead_time_days + safety_stock"""
    raise NotImplementedError


def get_reorder_list():
    """Products with stock <= reorder point, most urgent first (use heapq).
    Return list of dicts: sku, name, stock, reorder_point, suggested_order_qty."""
    raise NotImplementedError


def abc_analysis():
    """Rank products by revenue; label A (top ~80%), B (next ~15%), C (rest).
    Return list of dicts: sku, name, revenue, cumulative_pct, abc_class."""
    raise NotImplementedError


def dead_stock(days=30):
    """Products in stock with no sales in the last `days` days."""
    raise NotImplementedError


def moving_average(sku, window=7):
    """Daily sales series for sku with a `window`-day moving average.
    Return list of dicts: date, units_sold, moving_avg."""
    raise NotImplementedError
