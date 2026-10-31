"""Streamlit entry point (Person 3): Login & Inventory Dashboard.
Uses backend functions from backend.inventory, backend.auth, and backend.analytics.
NO SQL queries are written in the UI.
"""
import pandas as pd
import streamlit as st

from backend import auth, inventory as inv
from pages._utils import (
    ensure_demo_users,
    get_reorder_list_bridge,
    init_session,
    is_admin,
    is_authenticated,
    populate_demo_data,
    render_sidebar,
)

# Page configuration
st.set_page_config(
    page_title="StockSense — Smart Inventory",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ensure database tables and default accounts exist
ensure_demo_users()
init_session()
render_sidebar()

# ---------------------------------------------------------------------------
# LOGIN VIEW (When unauthenticated)
# ---------------------------------------------------------------------------
if not is_authenticated():
    st.title("📦 StockSense")
    st.subheader("Smart Inventory Management System")
    st.markdown(
        "Welcome! Track stock, monitor low-inventory alerts, and analyze sales performance in real time."
    )
    st.divider()

    col_login, col_info = st.columns([1, 1], gap="large")

    with col_login:
        st.markdown("### 🔐 User Login")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g. admin or staff")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not username.strip() or not password:
                    st.error("Please enter both username and password.")
                else:
                    user = auth.authenticate(username, password)
                    if user:
                        st.session_state.user = user
                        st.toast(f"Welcome back, {user['username']}!", icon="👋")
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")

        st.caption("Default accounts: `admin` / `admin123` (Admin) | `staff` / `staff123` (Staff)")

        # Quick demo login helpers
        st.markdown("#### ⚡ Quick Demo Access")
        quick_c1, quick_c2 = st.columns(2)
        with quick_c1:
            if st.button("👑 Demo as Admin", use_container_width=True):
                user = auth.authenticate("admin", "admin123")
                if user:
                    st.session_state.user = user
                    st.rerun()
        with quick_c2:
            if st.button("👤 Demo as Staff", use_container_width=True):
                user = auth.authenticate("staff", "staff123")
                if user:
                    st.session_state.user = user
                    st.rerun()

    with col_info:
        st.markdown("### 📋 Features Overview")
        st.markdown(
            """
            - **📊 Real-time Dashboard**: Live product counts, inventory valuation, and today's sales.
            - **🚨 Reorder Alerts**: Priority alerts for products nearing or below minimum safety thresholds.
            - **🏷️ Product Catalog**: Complete inventory browsing with search and category filtering.
            - **💳 Sales & Purchases**: Stock-guarded transactions with friendly error handling.
            - **📈 Visual Analytics**: ABC revenue classification, sales trends with moving averages, and dead stock reports.
            - **🔒 Role-Based Access Control**: Sensitive catalog operations restricted to administrators.
            """
        )

# ---------------------------------------------------------------------------
# DASHBOARD VIEW (When authenticated)
# ---------------------------------------------------------------------------
else:
    user = st.session_state.user
    role_title = "Administrator" if user["role"] == "admin" else "Staff Member"

    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.title("📊 Inventory Dashboard")
        st.caption(f"StockSense Operations Center | Logged in as **{user['username']}** ({role_title})")
    with header_col2:
        if is_admin():
            if st.button("✨ Load Sample Demo Data", help="Populate sample products and sales transactions"):
                populate_demo_data()
                st.success("Sample data loaded successfully!")
                st.rerun()

    st.divider()

    # Dashboard headline metrics using inv.dashboard_summary()
    try:
        summary = inv.dashboard_summary()
    except Exception as e:
        st.error(f"Failed to load dashboard metrics: {e}")
        summary = {"total_products": 0, "stock_value": 0.0, "today_sales": 0.0}

    total_prods = summary.get("total_products", 0)
    stock_val = summary.get("stock_value", 0.0)
    today_sales = summary.get("today_sales", 0.0)

    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric(
            label="Total Products",
            value=f"{total_prods:,}",
            help="Total number of active SKU items in inventory",
        )
    with m_col2:
        st.metric(
            label="Total Stock Value",
            value=f"₹{stock_val:,.2f}",
            help="Total inventory asset value (calculated as sum of stock * unit cost)",
        )
    with m_col3:
        st.metric(
            label="Today's Sales Revenue",
            value=f"₹{today_sales:,.2f}",
            help="Total gross sales revenue recorded for today",
        )

    st.divider()

    # Reorder Now Section
    st.subheader("🚨 Reorder Now")
    st.caption("Products whose current stock is at or below their calculated reorder threshold.")

    reorder_items = get_reorder_list_bridge()

    if reorder_items:
        st.warning(f"⚠️ **Attention Required**: **{len(reorder_items)}** item(s) are at or below reorder level!")
        
        # Format table for display
        display_data = []
        for item in reorder_items:
            display_data.append({
                "SKU": item["sku"],
                "Product Name": item["name"],
                "Category": item.get("category", "General"),
                "Current Stock": item["stock"],
                "Reorder Point": item["reorder_point"],
                "Suggested Order Qty": item["suggested_order_qty"],
                "Supplier": item.get("supplier_name", "None"),
            })
        
        df_reorder = pd.DataFrame(display_data)
        st.dataframe(
            df_reorder,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Current Stock": st.column_config.NumberColumn(format="%d units"),
                "Reorder Point": st.column_config.NumberColumn(format="%d units"),
                "Suggested Order Qty": st.column_config.NumberColumn(format="%d units"),
            }
        )

        col_act1, col_act2 = st.columns([1, 4])
        with col_act1:
            if st.button("📦 Go to Purchases to Restock", type="primary"):
                st.switch_page("pages/2_Sales_and_Purchases.py")
    else:
        st.success("✅ **All stock levels are healthy!** No items currently require immediate reordering.")

    st.divider()

    # Recent Transactions Preview
    st.subheader("🕒 Recent Transactions")
    recent_txs = inv.list_transactions(limit=6)

    if recent_txs:
        tx_rows = []
        for tx in recent_txs:
            tx_type = tx["type"]
            badge = "🟢 SALE" if tx_type == "SALE" else "🔵 PURCHASE"
            subtotal = tx["quantity"] * tx["unit_price"]
            tx_rows.append({
                "Date & Time": tx["timestamp"],
                "Type": badge,
                "SKU": tx["sku"],
                "Product": tx.get("product_name", tx["sku"]),
                "Quantity": tx["quantity"],
                "Unit Price": f"₹{tx['unit_price']:,.2f}",
                "Total Value": f"₹{subtotal:,.2f}",
            })
        st.dataframe(pd.DataFrame(tx_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No transactions recorded yet. Go to **Sales & Purchases** to record your first transaction!")
