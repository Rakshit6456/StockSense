"""Shared UI utilities, authentication checks, and analytics bridge (Person 3).
All data access uses backend functions from backend.inventory, backend.auth, and backend.analytics.
NO SQL queries are written in the UI.
"""
from datetime import datetime, timedelta
import heapq
import streamlit as st

from backend import auth, inventory as inv
import backend.analytics as analytics


def ensure_demo_users():
    """Ensure default admin and staff accounts exist for testing."""
    auth.ensure_default_admin()
    # Check if a demo staff account exists; create if not
    try:
        auth.create_user("staff", "staff123", role="staff")
    except ValueError:
        pass  # Already exists


def init_session():
    """Initialize session state keys."""
    if "user" not in st.session_state:
        st.session_state.user = None


def is_authenticated():
    """Return True if user is logged into the session."""
    return st.session_state.get("user") is not None


def is_admin():
    """Return True if logged in user has the admin role."""
    user = st.session_state.get("user")
    return user is not None and user.get("role") == "admin"


def render_auth_guard():
    """Protect sub-pages: if not authenticated, stop rendering and prompt login."""
    init_session()
    if not is_authenticated():
        st.warning("🔒 **Access Restricted**: Please log in to view this page.")
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("⬅️ Go to Login / Dashboard"):
                st.switch_page("app.py")
        st.stop()


def render_sidebar():
    """Display standard StockSense sidebar on all pages."""
    init_session()
    with st.sidebar:
        st.markdown("### 📦 StockSense")
        st.caption("Smart Inventory Management")
        st.divider()

        if is_authenticated():
            user = st.session_state.user
            role_badge = "👑 Admin" if user.get("role") == "admin" else "👤 Staff"
            st.markdown(f"**Logged in as:** `{user.get('username')}`")
            st.markdown(f"**Role:** {role_badge}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚪 Log out", use_container_width=True, key="sb_logout"):
                    st.session_state.user = None
                    st.rerun()

            st.divider()
            st.markdown("#### 🧭 Quick Navigation")
            st.page_link("app.py", label="Dashboard", icon="📊")
            st.page_link("pages/1_Products.py", label="Products", icon="🏷️")
            st.page_link("pages/2_Sales_and_Purchases.py", label="Sales & Purchases", icon="💳")
            st.page_link("pages/3_Analytics.py", label="Analytics", icon="📈")
        else:
            st.info("Please log in on the Dashboard to access pages.")


# ---------------------------------------------------------------------------
# Analytics Bridge: Calls backend.analytics first; if NotImplementedError,
# computes using backend.inventory methods without SQL queries.
# ---------------------------------------------------------------------------

def get_reorder_list_bridge():
    """Fetch reorder recommendations using backend.analytics or inventory API."""
    try:
        return analytics.get_reorder_list()
    except (NotImplementedError, AttributeError):
        # Fallback calculation using inv.list_products() and inv.list_transactions()
        products = inv.list_products()
        txs = inv.list_transactions(tx_type="SALE")
        
        # Calculate daily sales in last 30 days per product
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        sales_30d = {}
        for t in txs:
            if t["timestamp"] >= cutoff:
                sku = t["sku"]
                sales_30d[sku] = sales_30d.get(sku, 0) + t["quantity"]
        
        reorder_items = []
        for p in products:
            sku = p["sku"]
            sold = sales_30d.get(sku, 0)
            avg_daily = sold / 30.0
            lead_time = p.get("lead_time_days") or 3
            safety = p.get("safety_stock") or 0
            reorder_pt = int(round((avg_daily * lead_time) + safety))
            current_stock = p.get("stock", 0)
            
            if current_stock <= reorder_pt:
                # suggested order quantity brings stock to at least 2x reorder point or minimum
                suggested = max(reorder_pt * 2 - current_stock, safety + 10, 10)
                urgency = current_stock - reorder_pt  # Lower/more negative means more critical
                item = {
                    "sku": sku,
                    "name": p["name"],
                    "category": p.get("category") or "General",
                    "stock": current_stock,
                    "reorder_point": reorder_pt,
                    "suggested_order_qty": suggested,
                    "supplier_name": p.get("supplier_name") or "None",
                    "_urgency": urgency
                }
                reorder_items.append(item)
        
        # Sort by urgency (heapq priority simulation)
        reorder_items.sort(key=lambda x: x["_urgency"])
        return reorder_items


def get_abc_analysis_bridge():
    """Fetch ABC revenue classification using backend.analytics or inventory API."""
    try:
        return analytics.abc_analysis()
    except (NotImplementedError, AttributeError):
        products = inv.list_products()
        sales = inv.list_transactions(tx_type="SALE")
        
        # Aggregate revenue per product
        rev_by_sku = {p["sku"]: 0.0 for p in products}
        names_by_sku = {p["sku"]: p["name"] for p in products}
        
        for s in sales:
            sku = s["sku"]
            rev = s["quantity"] * s["unit_price"]
            rev_by_sku[sku] = rev_by_sku.get(sku, 0.0) + rev
            if sku not in names_by_sku:
                names_by_sku[sku] = s.get("product_name", sku)
        
        total_rev = sum(rev_by_sku.values())
        sorted_skus = sorted(rev_by_sku.items(), key=lambda x: x[1], reverse=True)
        
        cumulative = 0.0
        result = []
        for sku, revenue in sorted_skus:
            cumulative += revenue
            cum_pct = (cumulative / total_rev * 100.0) if total_rev > 0 else 100.0
            
            # Classification: A: <= 80%, B: >80% and <= 95%, C: >95%
            if cum_pct <= 80.0 or (len(result) == 0 and revenue > 0):
                abc_class = "A"
            elif cum_pct <= 95.0:
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


def get_dead_stock_bridge(days=30):
    """Fetch dead stock items using backend.analytics or inventory API."""
    try:
        return analytics.dead_stock(days=days)
    except (NotImplementedError, AttributeError):
        products = inv.list_products()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        dead = []
        for p in products:
            if p["stock"] > 0:
                recent_sales = inv.list_transactions(sku=p["sku"], tx_type="SALE", since=cutoff)
                if not recent_sales:
                    # Find last sale if any
                    all_sales = inv.list_transactions(sku=p["sku"], tx_type="SALE", limit=1)
                    last_sold = all_sales[0]["timestamp"][:10] if all_sales else "Never"
                    capital_tied = round(p["stock"] * (p.get("cost") or 0.0), 2)
                    dead.append({
                        "sku": p["sku"],
                        "name": p["name"],
                        "category": p.get("category") or "General",
                        "stock": p["stock"],
                        "cost": p.get("cost") or 0.0,
                        "capital_tied_up": capital_tied,
                        "last_sale": last_sold,
                    })
        # Sort by capital tied up descending (highest impact first)
        dead.sort(key=lambda x: x["capital_tied_up"], reverse=True)
        return dead


def get_sales_trend_bridge(sku=None, window=7):
    """Fetch sales time-series and rolling moving average."""
    try:
        if sku:
            return analytics.moving_average(sku, window=window)
    except (NotImplementedError, AttributeError):
        pass

    # Generic time-series calculation from inv.list_transactions()
    txs = inv.list_transactions(sku=sku, tx_type="SALE")
    if not txs:
        return []

    # Aggregate by date
    daily = {}
    for t in txs:
        dt = t["timestamp"][:10]  # YYYY-MM-DD
        if dt not in daily:
            daily[dt] = {"units_sold": 0, "revenue": 0.0}
        daily[dt]["units_sold"] += t["quantity"]
        daily[dt]["revenue"] += t["quantity"] * t["unit_price"]

    sorted_dates = sorted(daily.keys())
    result = []
    recent_units = []
    
    for d in sorted_dates:
        units = daily[d]["units_sold"]
        rev = daily[d]["revenue"]
        recent_units.append(units)
        if len(recent_units) > window:
            recent_units.pop(0)
        m_avg = round(sum(recent_units) / len(recent_units), 2)
        result.append({
            "date": d,
            "units_sold": units,
            "revenue": round(rev, 2),
            "moving_avg": m_avg
        })
    return result


def populate_demo_data():
    """Populate database with sample products and transactions for demo purposes."""
    ensure_demo_users()
    suppliers_data = [
        ("AgroGlobal Ltd", "+91 98765 43210", "orders@agroglobal.com"),
        ("FreshFoods Co", "+91 98111 22334", "supply@freshfoods.com"),
        ("Metro Wholesale", "+91 99222 33445", "sales@metrowholesale.in"),
    ]
    supplier_ids = {}
    existing_suppliers = {s["name"]: s["id"] for s in inv.list_suppliers()}
    for name, phone, email in suppliers_data:
        if name in existing_suppliers:
            supplier_ids[name] = existing_suppliers[name]
        else:
            sid = inv.add_supplier(name, phone, email)
            supplier_ids[name] = sid

    sample_products = [
        ("RICE01", "Basmati Rice 5kg", "Grains", 550.0, 420.0, 25, 4, 15, supplier_ids.get("AgroGlobal Ltd")),
        ("WHEAT01", "Whole Wheat Flour 10kg", "Flour", 420.0, 310.0, 18, 3, 10, supplier_ids.get("AgroGlobal Ltd")),
        ("OIL01", "Sunflower Oil 1L", "Oils", 160.0, 125.0, 8, 3, 20, supplier_ids.get("FreshFoods Co")),
        ("SUGAR01", "Organic Cane Sugar 1kg", "Pantry", 65.0, 45.0, 50, 2, 15, supplier_ids.get("Metro Wholesale")),
        ("TEA01", "Assam Black Tea 500g", "Beverages", 280.0, 190.0, 4, 5, 10, supplier_ids.get("FreshFoods Co")),
        ("COFFEE01", "Arabica Roast Coffee 250g", "Beverages", 450.0, 320.0, 30, 7, 5, supplier_ids.get("FreshFoods Co")),
        ("PASTA01", "Durum Wheat Penne 500g", "Pantry", 120.0, 75.0, 45, 5, 10, supplier_ids.get("Metro Wholesale")),
        ("SALT01", "Iodized Salt 1kg", "Pantry", 25.0, 14.0, 80, 2, 20, supplier_ids.get("Metro Wholesale")),
        ("OATS01", "Rolled Oats 1kg", "Grains", 195.0, 130.0, 12, 4, 15, supplier_ids.get("AgroGlobal Ltd")),
        ("HONEY01", "Pure Wildflower Honey 500g", "Pantry", 350.0, 220.0, 22, 6, 8, supplier_ids.get("FreshFoods Co")),
        ("ALMOND01", "California Almonds 500g", "Dry Fruits", 620.0, 480.0, 2, 7, 10, supplier_ids.get("AgroGlobal Ltd")),
        ("SPICE01", "Garam Masala 100g", "Spices", 95.0, 55.0, 60, 3, 12, supplier_ids.get("Metro Wholesale")),
    ]

    existing_skus = inv.build_sku_index()
    for item in sample_products:
        sku = item[0]
        if sku not in existing_skus:
            inv.add_product(
                sku=sku,
                name=item[1],
                category=item[2],
                price=item[3],
                cost=item[4],
                stock=item[5],
                lead_time_days=item[6],
                safety_stock=item[7],
                supplier_id=item[8]
            )

    # Generate historical sales over the last 30 days
    today = datetime.now()
    sales_plan = [
        ("RICE01", 3, 28), ("RICE01", 2, 21), ("RICE01", 4, 14), ("RICE01", 3, 7), ("RICE01", 2, 1),
        ("WHEAT01", 2, 25), ("WHEAT01", 3, 18), ("WHEAT01", 2, 9), ("WHEAT01", 4, 2),
        ("OIL01", 5, 26), ("OIL01", 6, 19), ("OIL01", 4, 11), ("OIL01", 5, 3),
        ("SUGAR01", 2, 20), ("SUGAR01", 3, 12), ("SUGAR01", 2, 4),
        ("TEA01", 4, 27), ("TEA01", 3, 15), ("TEA01", 2, 5),
        ("ALMOND01", 1, 10), ("ALMOND01", 2, 2),
        ("OATS01", 2, 16), ("OATS01", 3, 6),
    ]

    # Only add historical transactions if transaction log is empty
    if not inv.list_transactions(limit=1):
        for sku, qty, days_ago in sales_plan:
            ts = (today - timedelta(days=days_ago, hours=3)).strftime("%Y-%m-%d %H:%M:%S")
            try:
                # Add a purchase first if stock would dip below 0
                inv.record_purchase(sku, qty + 5, timestamp=(today - timedelta(days=days_ago + 1)).strftime("%Y-%m-%d %H:%M:%S"))
                inv.record_sale(sku, qty, timestamp=ts)
            except Exception:
                pass
        # Add today's sale for dashboard card demo
        try:
            today_ts = today.strftime("%Y-%m-%d %H:%M:%S")
            inv.record_sale("OIL01", 1, timestamp=today_ts)
            inv.record_sale("RICE01", 1, timestamp=today_ts)
        except Exception:
            pass
