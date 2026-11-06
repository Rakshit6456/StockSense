"""Products management page (Person 3).
Features:
- Search and category filter
- Export filtered inventory to CSV
- Form to add new products (Admin only)
- Form to edit existing products (Admin only)
- Form to delete products (Admin only)
- Staff role hiding for admin-only actions
- Zero SQL in UI (uses backend.inventory API)
"""
import pandas as pd
import streamlit as st

from backend import inventory as inv
from backend.exports import inventory_csv
from pages._utils import is_admin, render_auth_guard, render_sidebar

st.set_page_config(page_title="Products — StockSense", page_icon="🏷️", layout="wide")

render_auth_guard()
render_sidebar()

st.title("🏷️ Products Catalog")
st.caption("Browse inventory stock levels, search items, and manage catalog definitions.")

# ---------------------------------------------------------------------------
# SEARCH AND FILTER CONTROLS
# ---------------------------------------------------------------------------
col_search, col_cat, col_stock_filter = st.columns([2, 1, 1])

# Fetch all products once to populate category filter options
all_products = inv.list_products()
categories = sorted(list({p["category"] for p in all_products if p.get("category")}))
category_options = ["All Categories"] + categories

with col_search:
    search_query = st.text_input("🔍 Search by SKU or Name", placeholder="e.g. RICE, Oil, Flour...")

with col_cat:
    selected_category = st.selectbox("📁 Filter by Category", category_options)

with col_stock_filter:
    stock_status = st.selectbox("📦 Stock Status", ["All Items", "Low Stock (<= Safety)", "Out of Stock (0)"])

# Query backend with search and category filters
active_cat = None if selected_category == "All Categories" else selected_category
filtered_products = inv.list_products(search=search_query.strip() or None, category=active_cat)

# Apply client-side stock status filter if selected
if stock_status == "Low Stock (<= Safety)":
    filtered_products = [
        p for p in filtered_products if p.get("stock", 0) <= (p.get("safety_stock") or 0)
    ]
elif stock_status == "Out of Stock (0)":
    filtered_products = [p for p in filtered_products if p.get("stock", 0) == 0]

# ---------------------------------------------------------------------------
# SUPPLIER FILTER + EXPORT CSV BUTTON
# ---------------------------------------------------------------------------
all_supplier_names = sorted({
    p.get("supplier_name") for p in all_products if p.get("supplier_name")
})
selected_supplier = st.selectbox("\U0001f3ed Filter by Supplier", ["All Suppliers"] + all_supplier_names)
active_supplier = None if selected_supplier == "All Suppliers" else selected_supplier

if active_supplier:
    filtered_products = [
        p for p in filtered_products
        if (p.get("supplier_name") or "") == active_supplier
    ]

count_col, export_col = st.columns([3, 1])
with count_col:
    st.markdown(f"**Found {len(filtered_products)} product(s)**")
with export_col:
    status_map = {
        "All Items": None,
        "Low Stock (<= Safety)": "Low Stock",
        "Out of Stock (0)": "Out of Stock",
    }
    export_status = status_map.get(stock_status)
    if not filtered_products:
        st.button("\u2b07\ufe0f Export CSV", disabled=True,
                  help="No products to export", use_container_width=True)
    else:
        try:
            fname, csv_bytes = inventory_csv(
                search=search_query.strip() or None,
                category=active_cat,
                supplier_name=active_supplier,
                stock_status=export_status,
            )
            st.download_button(
                label="\u2b07\ufe0f Export CSV",
                data=csv_bytes,
                file_name=fname,
                mime="text/csv; charset=utf-8",
                use_container_width=True,
                help=f"Download {len(filtered_products)} product(s) as CSV",
            )
        except Exception as e:
            st.error(f"\u274c Export failed: {e}")

if filtered_products:
    table_rows = []
    for p in filtered_products:
        table_rows.append({
            "SKU": p["sku"],
            "Product Name": p["name"],
            "Category": p.get("category") or "—",
            "Selling Price": p["price"],
            "Cost Price": p.get("cost", 0.0),
            "Current Stock": p.get("stock", 0),
            "Safety Stock": p.get("safety_stock", 0),
            "Lead Time": f"{p.get('lead_time_days', 3)} days",
            "Supplier": p.get("supplier_name") or "None",
        })

    df = pd.DataFrame(table_rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Selling Price": st.column_config.NumberColumn(format="₹%.2f"),
            "Cost Price": st.column_config.NumberColumn(format="₹%.2f"),
            "Current Stock": st.column_config.NumberColumn(format="%d units"),
            "Safety Stock": st.column_config.NumberColumn(format="%d units"),
        },
    )
else:
    st.info("No products match the selected search or filter criteria.")

st.divider()

# ---------------------------------------------------------------------------
# CATALOG MANAGEMENT (Admin Only vs Staff)
# ---------------------------------------------------------------------------
if is_admin():
    st.subheader("⚙️ Product Catalog Management (Admin Only)")
    st.caption("Add, update, or remove product definitions from the system.")

    tab_add, tab_edit, tab_delete = st.tabs(["➕ Add New Product", "✏️ Edit Product", "🗑️ Delete Product"])

    # Fetch suppliers for dropdowns
    suppliers = inv.list_suppliers()
    supplier_map = {f"{s['name']} (ID: {s['id']})": s["id"] for s in suppliers}
    supplier_display_opts = ["None"] + list(supplier_map.keys())

    # --- TAB 1: ADD PRODUCT ---
    with tab_add:
        st.markdown("#### Enter New Product Details")
        with st.form("add_product_form", clear_on_submit=True):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                new_sku = st.text_input("Product SKU *", placeholder="e.g. MILK01 (auto-capitalized)")
                new_name = st.text_input("Product Name *", placeholder="e.g. Fresh Dairy Milk 1L")
                new_category = st.text_input("Category", placeholder="e.g. Dairy, Beverages, Pantry")
                new_supplier = st.selectbox("Supplier", supplier_display_opts)

            with col_a2:
                new_price = st.number_input("Selling Price (₹) *", min_value=0.0, value=100.0, step=1.0)
                new_cost = st.number_input("Cost Price (₹)", min_value=0.0, value=75.0, step=1.0)
                new_stock = st.number_input("Initial Stock Quantity", min_value=0, value=10, step=1)
                new_lead_time = st.number_input("Supplier Lead Time (Days)", min_value=0, value=3, step=1)
                new_safety = st.number_input("Safety Stock Threshold", min_value=0, value=5, step=1)

            add_submitted = st.form_submit_button("Add Product to Inventory", use_container_width=True)

            if add_submitted:
                sku_clean = new_sku.strip().upper()
                name_clean = new_name.strip()
                if not sku_clean or not name_clean:
                    st.error("SKU and Name are mandatory fields.")
                else:
                    sup_id = supplier_map.get(new_supplier)
                    try:
                        inv.add_product(
                            sku=sku_clean,
                            name=name_clean,
                            price=float(new_price),
                            category=new_category.strip() or None,
                            cost=float(new_cost),
                            stock=int(new_stock),
                            lead_time_days=int(new_lead_time),
                            safety_stock=int(new_safety),
                            supplier_id=sup_id,
                        )
                        st.success(f"✅ Product **{sku_clean}** ({name_clean}) added successfully!")
                        st.rerun()
                    except inv.DuplicateError as e:
                        st.error(f"❌ {e}")
                    except inv.InventoryError as e:
                        st.error(f"❌ Failed to add product: {e}")

    # --- TAB 2: EDIT PRODUCT ---
    with tab_edit:
        st.markdown("#### Update Existing Product Attributes")
        if not all_products:
            st.info("No products available to edit.")
        else:
            product_labels = {f"[{p['sku']}] {p['name']}": p["sku"] for p in all_products}
            selected_label = st.selectbox("Select Product to Edit", list(product_labels.keys()), key="edit_select")
            target_sku = product_labels.get(selected_label) or (all_products[0]["sku"] if all_products else "")

            try:
                prod = inv.get_product_by_sku(target_sku) if target_sku else None
            except inv.ProductNotFoundError:
                prod = None

            if prod:
                with st.form("edit_product_form"):
                    st.info(
                        f"Editing **{prod['sku']}**. (Note: Current stock is {prod['stock']} units. "
                        "Stock quantity changes must be recorded via Sales or Purchases to preserve audit records.)"
                    )
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        edit_name = st.text_input("Product Name", value=prod["name"])
                        edit_category = st.text_input("Category", value=prod.get("category") or "")
                        # Find current supplier index
                        cur_sup_idx = 0
                        if prod.get("supplier_id"):
                            for idx, (label, sid) in enumerate(supplier_map.items(), start=1):
                                if sid == prod["supplier_id"]:
                                    cur_sup_idx = idx
                                    break
                        edit_supplier = st.selectbox("Supplier", supplier_display_opts, index=cur_sup_idx)

                    with col_e2:
                        edit_price = st.number_input("Selling Price (₹)", min_value=0.0, value=float(prod["price"]), step=1.0)
                        edit_cost = st.number_input("Cost Price (₹)", min_value=0.0, value=float(prod.get("cost") or 0.0), step=1.0)
                        edit_lead = st.number_input("Lead Time (Days)", min_value=0, value=int(prod.get("lead_time_days") or 3), step=1)
                        edit_safety = st.number_input("Safety Stock", min_value=0, value=int(prod.get("safety_stock") or 0), step=1)

                    edit_submitted = st.form_submit_button("Save Changes", use_container_width=True)

                    if edit_submitted:
                        sup_id = supplier_map.get(edit_supplier)
                        try:
                            inv.update_product(
                                sku=target_sku,
                                name=edit_name.strip(),
                                category=edit_category.strip() or None,
                                price=float(edit_price),
                                cost=float(edit_cost),
                                lead_time_days=int(edit_lead),
                                safety_stock=int(edit_safety),
                                supplier_id=sup_id,
                            )
                            st.success(f"✅ Product **{target_sku}** successfully updated!")
                            st.rerun()
                        except inv.InventoryError as e:
                            st.error(f"❌ Error updating product: {e}")

    # --- TAB 3: DELETE PRODUCT ---
    with tab_delete:
        st.markdown("#### Remove Product from Catalog")
        if not all_products:
            st.info("No products available to delete.")
        else:
            del_labels = {f"[{p['sku']}] {p['name']} (Stock: {p['stock']})": p["sku"] for p in all_products}
            selected_del_label = st.selectbox("Select Product to Delete", list(del_labels.keys()), key="del_select")
            del_sku = del_labels.get(selected_del_label) or (all_products[0]["sku"] if all_products else "")

            st.warning(
                f"⚠️ **Warning**: Deleting **{del_sku}** will permanently erase this product and its associated transaction history!"
            )
            confirm_del = st.checkbox(f"Yes, I confirm I want to permanently delete SKU '{del_sku}'")

            if st.button("🗑️ Delete Product Permanently", type="primary", disabled=not confirm_del):
                try:
                    inv.delete_product(del_sku)
                    st.success(f"✅ Product '{del_sku}' has been deleted.")
                    st.rerun()
                except inv.InventoryError as e:
                    st.error(f"❌ Failed to delete product: {e}")

else:
    # Staff users see this message instead of management forms
    st.info(
        "🔒 **Staff Access Notice**: Catalog management actions (adding, editing, and deleting products) "
        "are restricted to administrators. Staff members have read-only view and search privileges on this page."
    )
