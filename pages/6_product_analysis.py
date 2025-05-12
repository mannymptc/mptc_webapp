import streamlit as st
import pandas as pd
import pyodbc
from datetime import datetime, timedelta
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
            "Connection Timeout=60"
        )
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

# ------------------ LOAD SALES DATA ------------------
@st.cache_data
def load_data():
    conn = connect_db()
    if conn is None:
        return pd.DataFrame()
    query = """
    SELECT order_id, product_sku, product_name, order_channel,
           order_date, product_qty, product_price
    FROM OrdersDespatch
    WHERE order_date >= '2023-06-01'
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['sale_amount'] = df['product_qty'] * df['product_price']
    return df

df = load_data()
if df.empty:
    st.stop()

# ------------------ SIDEBAR FILTERS ------------------
st.sidebar.header("🔎 Filters")

all_skus = sorted(df['product_sku'].dropna().unique().tolist())
default_skus = all_skus[:5] if len(all_skus) >= 5 else all_skus
selected_skus = st.sidebar.multiselect("Select SKU(s)", all_skus, default=default_skus)

all_names = sorted(df['product_name'].dropna().unique().tolist())
default_names = all_names[:5] if len(all_names) >= 5 else all_names
selected_names = st.sidebar.multiselect("Select Product Name(s)", all_names, default=default_names)

all_dates = df['order_date'].dt.normalize().dropna().unique()
selected_date_range = st.sidebar.date_input("Order Date Range", [min(all_dates), max(all_dates)])

# Final filtered data
filtered_df = df[
    (df['product_sku'].isin(selected_skus)) &
    (df['product_name'].isin(selected_names)) &
    (df['order_date'].between(selected_date_range[0], selected_date_range[1]))
]

# ------------------ TABS ------------------
tab1, tab2 = st.tabs(["📊 Sales History", "🧊 Unsold / Dead Stock"])

# ------------------ TAB 1: SALES HISTORY ------------------
with tab1:
    st.subheader("📈 Sales Summary")

    if filtered_df.empty:
        st.warning("No data available for selected filters.")
        st.stop()

    days_range = (selected_date_range[1] - selected_date_range[0]).days + 1

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

    st.markdown("### 📃 Filtered Sales Data")
    st.dataframe(filtered_df.head(10), use_container_width=True)

    csv_sales = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Sales History CSV", csv_sales, file_name="sales_history.csv", mime="text/csv")

# ------------------ TAB 2: DEAD STOCK ------------------
with tab2:
    st.subheader("🧊 Dead or Unsold Stock")

    last_sold = df.groupby(['product_sku', 'product_name'])['order_date'].max().reset_index()
    last_sold['Days Since Last Sale'] = (datetime.now().date() - last_sold['order_date'].dt.date).dt.days
    last_sold['Last Sold'] = last_sold['order_date'].dt.strftime('%Y-%m-%d')

    unsold_filter = st.selectbox(
        "📅 Show SKUs not sold in the last:",
        options=["7 days", "1 month", "3 months", "6 months", "12 months", "> 12 months"]
    )

    days_thresholds = {
        "7 days": 7,
        "1 month": 30,
        "3 months": 90,
        "6 months": 180,
        "12 months": 365,
        "> 12 months": 366
    }

    unsold_days = days_thresholds[unsold_filter]
    dead_stock = last_sold[last_sold['Days Since Last Sale'] >= unsold_days]

    if dead_stock.empty:
        st.info("✅ No dead stock found for selected filter.")
    else:
        st.dataframe(dead_stock[['product_sku', 'product_name', 'Last Sold', 'Days Since Last Sale']], use_container_width=True)

        csv_dead = dead_stock.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Dead Stock CSV", csv_dead, file_name="dead_stock.csv", mime="text/csv")
