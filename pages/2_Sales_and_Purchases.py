"""Sales and Purchases transaction management page (Person 3).
Features:
- Pick product by SKU with live stock level preview
- Enter quantity and price
- Friendly error messages (e.g. InsufficientStockError when overselling)
- Filterable transaction history log
- Zero SQL in UI (uses backend.inventory API)
"""
import pandas as pd
import streamlit as st

from backend import inventory as inv
from pages._utils import render_auth_guard, render_sidebar

st.set_page_config(page_title="Sales & Purchases — StockSense", page_icon="💳", layout="wide")

render_auth_guard()
render_sidebar()

st.title("💳 Sales & Purchases")
st.caption(
    "Process retail sales and warehouse purchase receipts. Stock levels and audit trails update atomically."
)

# Fetch products for selection dropdowns
products = inv.list_products()

if not products:
    st.warning("⚠️ No products exist in the catalog yet! Please add products in the Products page first.")
    st.stop()

# Product lookup maps
sku_index = {p["sku"]: p for p in products}
product_options = [
    f"[{p['sku']}] {p['name']} (In Stock: {p['stock']} units)" for p in products
]
option_to_sku = {
    f"[{p['sku']}] {p['name']} (In Stock: {p['stock']} units)": p["sku"] for p in products
}

tab_sale, tab_purchase = st.tabs(["🛒 Record Sale (Outgoing)", "📦 Record Purchase (Incoming)"])

cur_user = st.session_state.get("user") or {}
user_id = cur_user.get("id")

# ---------------------------------------------------------------------------
# TAB 1: RECORD SALE
# ---------------------------------------------------------------------------
with tab_sale:
    st.markdown("#### 🛒 New Customer Sale")
    st.caption("Deducts stock automatically. Transaction is rejected if quantity exceeds available stock.")

    col_s1, col_s2 = st.columns([1, 1], gap="medium")

    with col_s1:
        selected_sale_opt = st.selectbox(
            "Select Product to Sell *",
            product_options,
            key="sale_product_select",
        )
        sale_sku = option_to_sku.get(selected_sale_opt) or (products[0]["sku"] if products else "")
        sale_prod = sku_index.get(sale_sku, products[0] if products else {})

        sale_qty = st.number_input(
            "Quantity to Sell *",
            min_value=1,
            value=1,
            step=1,
            key="sale_qty_input",
            help="Must be a positive whole number",
        )

        sale_unit_price = st.number_input(
            "Unit Selling Price (₹) *",
            min_value=0.0,
            value=float(sale_prod.get("price") or 0.0),
            step=1.0,
            key="sale_price_input",
            help="Defaults to catalog selling price. Can be adjusted for discounts.",
        )

        total_sale_amount = sale_qty * sale_unit_price
        st.markdown(f"**Total Sale Value:** `₹{total_sale_amount:,.2f}`")

        sale_submitted = st.button("Complete Sale", type="primary", use_container_width=True)

    with col_s2:
        st.markdown("##### 📌 Product Snapshot")
        cur_stock = sale_prod.get("stock", 0)
        safety_threshold = sale_prod.get("safety_stock", 0)

        c_stock, c_price = st.columns(2)
        with c_stock:
            st.metric(label="Current Stock", value=f"{cur_stock} units")
        with c_price:
            st.metric(label="Standard Price", value=f"₹{sale_prod.get('price', 0.0):,.2f}")

        # Stock alert indicator
        if cur_stock == 0:
            st.error("🚨 **Out of Stock!** This item cannot be sold until restocked.")
        elif cur_stock < sale_qty:
            st.warning(f"⚠️ Requested **{sale_qty}** units, but only **{cur_stock}** available in stock.")
        elif cur_stock - sale_qty <= safety_threshold:
            st.info(f"ℹ️ Selling will reduce stock to **{cur_stock - sale_qty}** (at or below safety stock {safety_threshold}).")

    if sale_submitted:
        try:
            inv.record_sale(
                sku=sale_sku,
                qty=int(sale_qty),
                unit_price=float(sale_unit_price),
                user_id=user_id,
            )
            new_stock = cur_stock - int(sale_qty)
            st.success(
                f"✅ **Sale recorded successfully!** Sold **{sale_qty}** units of [{sale_sku}] {sale_prod['name']} "
                f"for ₹{total_sale_amount:,.2f}. Remaining stock: **{new_stock}** units."
            )
            st.rerun()
        except inv.InsufficientStockError as e:
            st.error(f"❌ **Transaction Blocked**: {e}")
            st.info("💡 **Resolution**: Reduce the quantity or restock the product under the 'Record Purchase' tab.")
        except inv.ProductNotFoundError as e:
            st.error(f"❌ Product Error: {e}")
        except inv.InventoryError as e:
            st.error(f"❌ Inventory Error: {e}")
        except Exception as e:
            st.error(f"❌ Unexpected Error: {e}")

# ---------------------------------------------------------------------------
# TAB 2: RECORD PURCHASE / RESTOCK
# ---------------------------------------------------------------------------
with tab_purchase:
    st.markdown("#### 📦 Receive Supplier Purchase / Restock")
    st.caption("Increases warehouse stock and logs the purchase expenditure.")

    col_p1, col_p2 = st.columns([1, 1], gap="medium")

    with col_p1:
        selected_purchase_opt = st.selectbox(
            "Select Product to Restock *",
            product_options,
            key="purchase_product_select",
        )
        purchase_sku = option_to_sku.get(selected_purchase_opt) or (products[0]["sku"] if products else "")
        purchase_prod = sku_index.get(purchase_sku, products[0] if products else {})

        purchase_qty = st.number_input(
            "Quantity Received *",
            min_value=1,
            value=10,
            step=1,
            key="purchase_qty_input",
            help="Quantity of items received from supplier",
        )

        purchase_unit_cost = st.number_input(
            "Unit Cost Price (₹) *",
            min_value=0.0,
            value=float(purchase_prod.get("cost") or 0.0),
            step=1.0,
            key="purchase_cost_input",
            help="Defaults to catalog cost price. Can be adjusted to actual invoice cost.",
        )

        total_purchase_cost = purchase_qty * purchase_unit_cost
        st.markdown(f"**Total Restock Cost:** `₹{total_purchase_cost:,.2f}`")

        purchase_submitted = st.button("Receive & Restock", type="primary", use_container_width=True)

    with col_p2:
        st.markdown("##### 📌 Restock Preview")
        cur_stock_p = purchase_prod.get("stock", 0)
        expected_stock = cur_stock_p + int(purchase_qty)

        c_cur, c_exp = st.columns(2)
        with c_cur:
            st.metric(label="Current Stock", value=f"{cur_stock_p} units")
        with c_exp:
            st.metric(label="Post-Restock Stock", value=f"{expected_stock} units", delta=f"+{purchase_qty}")

        st.caption(f"Supplier: **{purchase_prod.get('supplier_name') or 'Not Assigned'}**")

    if purchase_submitted:
        try:
            inv.record_purchase(
                sku=purchase_sku,
                qty=int(purchase_qty),
                unit_cost=float(purchase_unit_cost),
                user_id=user_id,
            )
            st.success(
                f"✅ **Purchase recorded successfully!** Restocked **{purchase_qty}** units of "
                f"[{purchase_sku}] {purchase_prod['name']}. New stock: **{expected_stock}** units."
            )
            st.rerun()
        except inv.InventoryError as e:
            st.error(f"❌ Purchase Error: {e}")
        except Exception as e:
            st.error(f"❌ Unexpected Error: {e}")

st.divider()

# ---------------------------------------------------------------------------
# TRANSACTION AUDIT LOG
# ---------------------------------------------------------------------------
st.subheader("📜 Transaction Audit Log")
st.caption("Immutable transaction history of sales and purchases.")

f_col1, f_col2, f_col3 = st.columns([1, 1, 1])

with f_col1:
    filter_type = st.selectbox("Filter by Type", ["All Transactions", "Sales Only", "Purchases Only"])
with f_col2:
    sku_filter_opts = ["All Products"] + [p["sku"] for p in products]
    filter_sku = st.selectbox("Filter by SKU", sku_filter_opts)
with f_col3:
    filter_limit = st.selectbox("Display Limit", [15, 30, 50, 100], index=0)

type_param = None
if filter_type == "Sales Only":
    type_param = "SALE"
elif filter_type == "Purchases Only":
    type_param = "PURCHASE"

sku_param = None if filter_sku == "All Products" else filter_sku

transactions = inv.list_transactions(sku=sku_param, tx_type=type_param, limit=filter_limit)

if transactions:
    log_rows = []
    for tx in transactions:
        is_sale = tx["type"] == "SALE"
        total_val = tx["quantity"] * tx["unit_price"]
        log_rows.append({
            "Timestamp": tx["timestamp"],
            "Type": "🟢 SALE" if is_sale else "🔵 PURCHASE",
            "SKU": tx["sku"],
            "Product": tx.get("product_name", tx["sku"]),
            "Quantity": tx["quantity"],
            "Unit Price": tx["unit_price"],
            "Total Value": total_val,
        })

    df_log = pd.DataFrame(log_rows)
    st.dataframe(
        df_log,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Unit Price": st.column_config.NumberColumn(format="₹%.2f"),
            "Total Value": st.column_config.NumberColumn(format="₹%.2f"),
        },
    )
else:
    st.info("No transactions match the selected filters.")
