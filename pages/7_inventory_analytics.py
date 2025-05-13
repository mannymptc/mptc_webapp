# 7_inventory_analytics.py
import streamlit as st
import pandas as pd
import pyodbc
from datetime import datetime, timedelta
from forecasting_model import forecast_multiple_skus, prepare_forecast_csv

st.set_page_config(page_title="📈 Inventory Forecast & Planning", layout="wide")
st.title("🗃️ Inventory Forecast & Recommendation")

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
        od.order_date,
        od.product_qty
    FROM OrdersDespatch od
    LEFT JOIN Products p ON od.product_sku = p.product_sku
    WHERE od.order_date >= '2023-06-01'
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df['order_date'] = pd.to_datetime(df['order_date'])
    return df

# Load data
df = load_data()
if df.empty:
    st.stop()

# ------------------ FILTER SECTION ------------------
st.sidebar.header("🔍 Filter Products")
sku_input = st.sidebar.text_input("🔍 SKU Filter (comma-separated)")
name_input = st.sidebar.text_input("🔍 Name Filter")
cat_input = st.sidebar.text_input("🔍 Category Filter")

sku_terms = [term.strip().lower() for term in sku_input.split(',') if term.strip()]
name_terms = [term.strip().lower() for term in name_input.split(',') if term.strip()]
cat_terms = [term.strip().lower() for term in cat_input.split(',') if term.strip()]

filtered_df = df.copy()
if sku_terms:
    sku_mask = pd.Series(False, index=filtered_df.index)
    for term in sku_terms:
        sku_mask |= filtered_df['product_sku'].astype(str).str.lower().str.contains(term)
    filtered_df = filtered_df[sku_mask]
if name_terms:
    name_mask = pd.Series(False, index=filtered_df.index)
    for term in name_terms:
        name_mask |= filtered_df['product_name'].astype(str).str.lower().str.contains(term)
    filtered_df = filtered_df[name_mask]
if cat_terms:
    cat_mask = pd.Series(False, index=filtered_df.index)
    for term in cat_terms:
        cat_mask |= filtered_df['product_category'].astype(str).str.lower().str.contains(term)
    filtered_df = filtered_df[cat_mask]

if filtered_df.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# ------------------ FORECAST SETTINGS ------------------
st.sidebar.header("⏳ Forecast Settings")
range_option = st.sidebar.selectbox("Forecast Horizon", ["Next 7 Days", "Next 30 Days", "Next 90 Days"])
forecast_days = 7 if range_option == "Next 7 Days" else 30 if range_option == "Next 30 Days" else 90

# Optional: Safety stock %
safety_pct = st.sidebar.slider("📦 Safety Stock %", min_value=0, max_value=100, value=20, step=5)

# ------------------ RUN FORECAST ------------------
st.markdown("### 🔮 SKU-Level Sales Forecast")
forecast_df = forecast_multiple_skus(
    df=filtered_df,
    sku_col='product_sku',
    date_col='order_date',
    qty_col='product_qty',
    forecast_days=forecast_days
)

if forecast_df.empty:
    st.info("⚠️ No SKUs with sufficient historical data (≥30 days). Try different filters.")
    st.stop()

st.dataframe(forecast_df, use_container_width=True)

# ------------------ CSV DOWNLOAD ------------------
csv_data = prepare_forecast_csv(forecast_df)
st.download_button(
    label="⬇️ Download Forecast CSV",
    data=csv_data,
    file_name="forecast_results.csv",
    mime="text/csv",
    use_container_width=True
)

# ------------------ RECOMMENDED INVENTORY ------------------
st.markdown("### 🧮 Recommended Inventory Planning")

# Dummy inventory: Assume current_inventory = 100 for now (replace with actual lookup later)
forecast_summary = forecast_df.groupby('product_sku')['forecast_qty'].sum().reset_index()
forecast_summary['avg_daily_forecast'] = forecast_summary['forecast_qty'] / forecast_days
forecast_summary['safety_stock'] = forecast_summary['avg_daily_forecast'] * (forecast_days / 2) * (safety_pct / 100)
forecast_summary['recommended_inventory'] = forecast_summary['forecast_qty'] + forecast_summary['safety_stock']
forecast_summary['current_inventory'] = 100
forecast_summary['po_quantity'] = forecast_summary['recommended_inventory'] - forecast_summary['current_inventory']
forecast_summary['po_quantity'] = forecast_summary['po_quantity'].apply(lambda x: max(0, round(x)))

st.dataframe(forecast_summary[['product_sku', 'forecast_qty', 'recommended_inventory', 'current_inventory', 'po_quantity']], use_container_width=True)
