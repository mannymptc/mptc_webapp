import streamlit as st
import pandas as pd
import pyodbc
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="📊 Product Sales Analysis", layout="wide")
st.title("📦 Product Sales History & Dead Stock")

# ------------------ DB CONNECTION ------------------
def connect_db():
    try:
        return pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=mptcecommerce-sql-server.database.windows.net;"
            "DATABASE=mptcecommerce-db;"
            "UID=mptcadmin;"
            "PWD=Mptc@2025;"
            "Connection Timeout=30"
        )
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

# ------------------ LOAD DATA ------------------
@st.cache_data
def load_data():
    conn = connect_db()
    if conn is None:
        return pd.DataFrame()
    query = """
    SELECT 
        od.order_id,
        od.product_sku,
        od.product_name,
        p.product_category,
        od.order_channel,
        od.order_date,
        od.product_qty,
        od.product_price
    FROM OrdersDespatch od
    LEFT JOIN Products p ON od.product_sku = p.product_sku
    WHERE od.order_date >= '2023-06-01'
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['sale_amount'] = df['product_qty'] * df['product_price']
    return df

df = load_data()
if df.empty:
    st.stop()

# ------------------ SIDEBAR DATE FILTER ------------------
st.sidebar.header("📅 Order Date Filter")
all_dates = df['order_date'].dt.normalize().dropna().unique()
selected_date_range = st.sidebar.date_input("Select Order Date Range", [min(all_dates), max(all_dates)])
start_date = pd.to_datetime(selected_date_range[0])
end_date = pd.to_datetime(selected_date_range[1])

# ------------------ TABS ------------------
tab1, tab2 = st.tabs(["📊 Sales History", "🧊 Unsold / Dead Stock"])

# ------------------ TAB 1: SALES HISTORY ------------------
with tab1:
    st.subheader("📈 Sales Summary")

    # ------------------ FILTERS ------------------
    st.markdown("### 🎯 Filter Products (Only for Tab 1)")

    sku_list = sorted(df['product_sku'].dropna().unique().tolist())
    name_list = sorted(df['product_name'].dropna().unique().tolist())
    category_list = sorted(df['product_category'].dropna().unique().tolist())

    top5_skus = (
        df.groupby('product_sku')['product_qty'].sum()
        .sort_values(ascending=False)
        .head(5)
        .index.tolist()
    )

    col1, col2, col3 = st.columns(3)
    selected_skus = col1.multiselect("Select SKU(s)", sku_list, default=top5_skus)
    selected_names = col2.multiselect("Select Product Name(s)", name_list)
    selected_categories = col3.multiselect("Select Category(s)", category_list)

    filtered_df = df[
        df['product_sku'].isin(selected_skus) &
        (df['product_name'].isin(selected_names) if selected_names else True) &
        (df['product_category'].isin(selected_categories) if selected_categories else True) &
        (df['order_date'].between(start_date, end_date))
    ]

    if filtered_df.empty:
        st.warning("No data available for selected filters.")
    else:
        days_range = (end_date - start_date).days + 1
        total_qty = filtered_df['product_qty'].sum()
        total_revenue = filtered_df['sale_amount'].sum()

        avg_qty_day = total_qty / days_range
        avg_rev_day = total_revenue / days_range
        avg_qty_week = avg_qty_day * 7
        avg_rev_week = avg_rev_day * 7
        avg_qty_month = avg_qty_day * 30
        avg_rev_month = avg_rev_day * 30

        col1, col2, col3 = st.columns(3)
        col1.metric("🔢 Total Quantity Sold", int(total_qty))
        col2.metric("💰 Total Revenue", f"£ {total_revenue:,.2f}")
        col3.metric("📅 Days Selected", f"{days_range} days")

        col4, col5, col6 = st.columns(3)
        col4.metric("📦 Avg Qty / Day", f"{avg_qty_day:.2f}")
        col5.metric("📦 Avg Qty / Week", f"{avg_qty_week:.2f}")
        col6.metric("📦 Avg Qty / Month", f"{avg_qty_month:.2f}")

        col7, col8, col9 = st.columns(3)
        col7.metric("💵 Avg Rev / Day", f"£ {avg_rev_day:.2f}")
        col8.metric("💵 Avg Rev / Week", f"£ {avg_rev_week:.2f}")
        col9.metric("💵 Avg Rev / Month", f"£ {avg_rev_month:.2f}")

        # ------------------ CHANNEL-WISE SUMMARY ------------------
        st.markdown("### 📊 Channel-wise Sales Summary")
        channel_summary = (
            filtered_df.groupby('order_channel')
            .agg(
                total_orders=('order_id', pd.Series.nunique),
                total_qty=('product_qty', 'sum'),
                total_revenue=('sale_amount', 'sum')
            )
            .reset_index()
            .sort_values(by='total_revenue', ascending=False)
        )
        st.dataframe(channel_summary, use_container_width=True)

        # ------------------ RAW DATA ------------------
        st.markdown("### 📃 Raw Sales Data")
        st.dataframe(filtered_df.head(10), use_container_width=True)

        csv_sales = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Sales History CSV", csv_sales, file_name="sales_history.csv", mime="text/csv")

# ------------------ TAB 2: DEAD STOCK ------------------
with tab2:
    st.subheader("🧊 Dead or Unsold Stock")

    # Get last sold date per product
    last_sold = df.groupby(['product_sku', 'product_name'])['order_date'].max().reset_index()
    last_sold['Days Since Last Sale'] = (pd.Timestamp.now().normalize() - last_sold['order_date']).dt.days
    last_sold['Last Sold'] = last_sold['order_date'].dt.strftime('%Y-%m-%d')

    # Define ranges for unsold buckets
    unsold_buckets = {
        "7 to 1 month": (7, 30),
        "1 to 3 months": (31, 90),
        "3 to 6 months": (91, 180),
        "6 months to 1 year": (181, 365),
        "more than 1 year": (366, float("inf"))
    }

    selected_buckets = st.multiselect(
        "📅 Select Unsold Time Range(s):",
        options=list(unsold_buckets.keys()),
        default=["1 to 3 months"]
    )

    # Filter using combined logic
    if not selected_buckets:
        st.warning("Please select at least one unsold duration.")
    else:
        combined_filter = pd.Series(False, index=last_sold.index)

        for bucket in selected_buckets:
            min_days, max_days = unsold_buckets[bucket]
            in_range = (last_sold['Days Since Last Sale'] >= min_days) & (last_sold['Days Since Last Sale'] <= max_days)
            combined_filter |= in_range

        dead_stock = last_sold[combined_filter]

        if dead_stock.empty:
            st.info("✅ No dead stock found for selected range(s).")
        else:
            st.caption("Showing SKUs not sold in the selected time window(s):")
            st.dataframe(dead_stock[['product_sku', 'product_name', 'Last Sold', 'Days Since Last Sale']], use_container_width=True)

            csv_dead = dead_stock.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Dead Stock CSV", csv_dead, file_name="dead_stock.csv", mime="text/csv")
