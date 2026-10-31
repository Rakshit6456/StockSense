"""Analytics & Intelligence page (Person 3).
Features:
- Sales trend time-series charts with moving average
- ABC classification breakdown (Revenue Pareto distribution)
- Dead stock table with capital tied up calculation
- Zero SQL in UI (uses backend functions from backend.analytics and backend.inventory)
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backend import inventory as inv
from pages._utils import (
    get_abc_analysis_bridge,
    get_dead_stock_bridge,
    get_sales_trend_bridge,
    render_auth_guard,
    render_sidebar,
)

st.set_page_config(page_title="Analytics — StockSense", page_icon="📈", layout="wide")

render_auth_guard()
render_sidebar()

st.title("📈 Inventory & Sales Analytics")
st.caption(
    "Data-driven insights: sales momentum trends, ABC revenue classification, and dead stock analysis."
)

tab_trend, tab_abc, tab_dead = st.tabs([
    "📊 Sales Trend & Moving Average",
    "🏆 ABC Revenue Analysis",
    "⏳ Dead Stock Report",
])

# ---------------------------------------------------------------------------
# TAB 1: SALES TREND & MOVING AVERAGE
# ---------------------------------------------------------------------------
with tab_trend:
    st.subheader("📊 Sales Momentum & Trend Analysis")
    st.caption("Track daily units sold and moving average trends over time.")

    products = inv.list_products()
    sku_choices = ["All Products"] + [p["sku"] for p in products]

    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        selected_sku_choice = st.selectbox("Select Product Scope", sku_choices, key="trend_sku_select")
    with col_t2:
        ma_window = st.slider("Moving Average Window (Days)", min_value=3, max_value=14, value=7, step=1)

    sku_param = None if selected_sku_choice == "All Products" else selected_sku_choice
    trend_data = get_sales_trend_bridge(sku=sku_param, window=ma_window)

    if trend_data:
        df_trend = pd.DataFrame(trend_data)
        df_trend["date"] = pd.to_datetime(df_trend["date"])

        total_units = int(df_trend["units_sold"].sum())
        total_rev = float(df_trend["revenue"].sum())
        avg_daily_units = round(df_trend["units_sold"].mean(), 1)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Units Sold", f"{total_units:,}")
        with c2:
            st.metric("Total Sales Revenue", f"₹{total_rev:,.2f}")
        with c3:
            st.metric(f"Avg Units / Day", f"{avg_daily_units}")

        # Plotly Dual Line Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_trend["date"],
            y=df_trend["units_sold"],
            name="Daily Units Sold",
            marker_color="rgba(31, 119, 180, 0.45)",
        ))
        fig.add_trace(go.Scatter(
            x=df_trend["date"],
            y=df_trend["moving_avg"],
            name=f"{ma_window}-Day Moving Average",
            mode="lines+markers",
            line=dict(color="#ff7f0e", width=3),
        ))

        fig.update_layout(
            title=f"Sales Volume & {ma_window}-Day Moving Average ({selected_sku_choice})",
            xaxis_title="Date",
            yaxis_title="Units Sold",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Revenue Trend Chart
        fig_rev = px.area(
            df_trend,
            x="date",
            y="revenue",
            title=f"Daily Revenue Trend (₹)",
            labels={"date": "Date", "revenue": "Revenue (₹)"},
            color_discrete_sequence=["#2ca02c"],
        )
        fig_rev.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_rev, use_container_width=True)

    else:
        st.info("No historical sales data found for the selected scope. Record sales to view trends!")

# ---------------------------------------------------------------------------
# TAB 2: ABC REVENUE ANALYSIS
# ---------------------------------------------------------------------------
with tab_abc:
    st.subheader("🏆 ABC Inventory Classification (Pareto 80/15/5)")
    st.caption(
        "Class A items drive ~80% of revenue (vital priority). "
        "Class B items drive ~15% (moderate priority). "
        "Class C items drive ~5% (low revenue, bulk control)."
    )

    abc_items = get_abc_analysis_bridge()

    if abc_items:
        df_abc = pd.DataFrame(abc_items)

        # Count items and revenue by class
        class_counts = df_abc["abc_class"].value_counts().to_dict()
        class_rev = df_abc.groupby("abc_class")["revenue"].sum().to_dict()
        total_revenue = df_abc["revenue"].sum()

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            a_cnt = class_counts.get("A", 0)
            a_rev = class_rev.get("A", 0.0)
            a_pct = (a_rev / total_revenue * 100) if total_revenue > 0 else 0
            st.metric(
                label="🟢 Class A (High Value)",
                value=f"{a_cnt} Items",
                delta=f"₹{a_rev:,.0f} ({a_pct:.1f}% rev)",
            )
        with col_b:
            b_cnt = class_counts.get("B", 0)
            b_rev = class_rev.get("B", 0.0)
            b_pct = (b_rev / total_revenue * 100) if total_revenue > 0 else 0
            st.metric(
                label="🟡 Class B (Moderate Value)",
                value=f"{b_cnt} Items",
                delta=f"₹{b_rev:,.0f} ({b_pct:.1f}% rev)",
            )
        with col_c:
            c_cnt = class_counts.get("C", 0)
            c_rev = class_rev.get("C", 0.0)
            c_pct = (c_rev / total_revenue * 100) if total_revenue > 0 else 0
            st.metric(
                label="⚪ Class C (Low Value)",
                value=f"{c_cnt} Items",
                delta=f"₹{c_rev:,.0f} ({c_pct:.1f}% rev)",
            )

        st.divider()

        ch_col1, ch_col2 = st.columns([1, 1])
        with ch_col1:
            # Pie Chart of Revenue Share
            pie_data = pd.DataFrame({
                "Class": [f"Class {k}" for k in class_rev.keys()],
                "Revenue": list(class_rev.values()),
            })
            fig_pie = px.pie(
                pie_data,
                values="Revenue",
                names="Class",
                title="Revenue Share by ABC Class",
                color="Class",
                color_discrete_map={
                    "Class A": "#2ca02c",
                    "Class B": "#ff7f0e",
                    "Class C": "#7f7f7f",
                },
                hole=0.45,
            )
            fig_pie.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)

        with ch_col2:
            # Bar Chart of Top Revenue Contributors
            top_contributors = df_abc.head(8)
            fig_bar = px.bar(
                top_contributors,
                x="revenue",
                y="name",
                orientation="h",
                color="abc_class",
                title="Top Products by Cumulative Revenue Contribution",
                labels={"revenue": "Revenue (₹)", "name": "Product"},
                color_discrete_map={"A": "#2ca02c", "B": "#ff7f0e", "C": "#7f7f7f"},
            )
            fig_bar.update_layout(yaxis=dict(autorange="reversed"), height=350, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("#### 📋 ABC Detailed Product Ranking")
        st.dataframe(
            df_abc,
            use_container_width=True,
            hide_index=True,
            column_config={
                "revenue": st.column_config.NumberColumn(label="Total Revenue", format="₹%.2f"),
                "cumulative_pct": st.column_config.NumberColumn(label="Cumulative Share", format="%.1f%%"),
                "abc_class": st.column_config.TextColumn(label="ABC Class"),
            },
        )
    else:
        st.info("No product revenue data available yet. Record sales to generate ABC classifications.")

# ---------------------------------------------------------------------------
# TAB 3: DEAD STOCK REPORT
# ---------------------------------------------------------------------------
with tab_dead:
    st.subheader("⏳ Dead Stock & Slow-Moving Inventory")
    st.caption("Products with inventory on hand that have registered zero sales during the selected period.")

    dead_days = st.slider("Inactivity Threshold (Days without sales)", min_value=7, max_value=90, value=30, step=7)

    dead_items = get_dead_stock_bridge(days=dead_days)

    if dead_items:
        df_dead = pd.DataFrame(dead_items)
        total_tied_capital = df_dead["capital_tied_up"].sum()
        total_dead_units = df_dead["stock"].sum()

        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            st.metric("Dead Stock Items", f"{len(df_dead)} SKUs")
        with dc2:
            st.metric("Total Stagnant Units", f"{total_dead_units:,} units")
        with dc3:
            st.metric(
                "Capital Tied Up",
                f"₹{total_tied_capital:,.2f}",
                help="Sum of stock * cost price for stagnant inventory",
            )

        st.warning(
            f"⚠️ **{len(df_dead)} product(s)** have not sold a single unit in the last **{dead_days} days**, "
            f"locking up **₹{total_tied_capital:,.2f}** in working capital."
        )

        st.dataframe(
            df_dead,
            use_container_width=True,
            hide_index=True,
            column_config={
                "cost": st.column_config.NumberColumn(label="Unit Cost", format="₹%.2f"),
                "capital_tied_up": st.column_config.NumberColumn(label="Capital Locked Up", format="₹%.2f"),
                "stock": st.column_config.NumberColumn(label="In-Stock Quantity", format="%d units"),
                "last_sale": st.column_config.TextColumn(label="Last Recorded Sale"),
            },
        )

        st.markdown(
            """
            💡 **Strategic Inventory Recommendations**:
            - **Promotional Bundles**: Pair slow-moving Class C items with high-velocity Class A products.
            - **Clearance Discount**: Offer markdown pricing to recover trapped working capital.
            - **Supplier Returns**: Check return policies for items approaching shelf-life boundaries.
            """
        )
    else:
        st.success(f"🎉 **Great news!** No dead stock detected. All stocked items have active sales within the last {dead_days} days.")
