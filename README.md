# StockSense — Smart Inventory Management System

Python + SQLite + Streamlit. Tracks stock, raises reorder alerts and gives sales analytics for retail/warehouse businesses.

## Setup
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py        # default login: admin / admin123
pytest                      # run tests
```

## Structure and owners
| Path | Owner | Purpose |
|---|---|---|
| `backend/database.py`, `inventory.py`, `auth.py` | Person 1 | schema, CRUD, sales/purchases, login |
| `backend/analytics.py`, `tests/test_analytics.py` | Person 2 | reorder point, ABC, dead stock, moving average |
| `app.py`, `pages/` | Person 3 | Streamlit UI |
| `backend/reports.py`, `tests/`, `data/`, `docs/` | Person 4 | exports, sample data, report |

## Backend API (what the UI calls)
```python
from backend import inventory as inv
inv.add_product(sku, name, price, category=None, cost=0, stock=0, lead_time_days=3, safety_stock=0, supplier_id=None)
inv.get_product_by_sku(sku); inv.list_products(search=None, category=None); inv.build_sku_index()
inv.update_product(sku, **fields); inv.delete_product(sku)
inv.add_supplier(name, phone, email); inv.list_suppliers()
inv.record_sale(sku, qty, user_id=None, timestamp=None)       # raises InsufficientStockError
inv.record_purchase(sku, qty, unit_cost=None, user_id=None, timestamp=None)
inv.list_transactions(sku=None, tx_type=None, since=None, limit=None)
inv.dashboard_summary()
```
Errors (all subclass `InventoryError`): `ProductNotFoundError`, `InsufficientStockError`, `DuplicateError`.
Stock changes only via sales/purchases. `timestamp="YYYY-MM-DD HH:MM:SS"` lets you load historical sales for analytics.

Analytics signatures are in `backend/analytics.py`.

## Git workflow
Never push to `main`. Work on `feature/<name>` branches, open a PR, get one review, merge. `git pull origin main` daily.
