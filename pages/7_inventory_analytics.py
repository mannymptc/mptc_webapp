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

# ------------------ TOP FILTERS ------------------
st.markdown("### 🎯 Smart Search Filters")
col1, col2, col3 = st.columns(3)
with col1:
    sku_input = st.text_input("🔍 SKU Filter", placeholder="e.g. abc, 123, xyz")
with col2:
    name_input = st.text_input("🔍 Name Filter", placeholder="e.g. bottle, charger")
with col3:
    cat_input = st.text_input("🔍 Category Filter", placeholder="e.g. electronics, bags")

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
st.markdown("### ⚙️ Forecast Settings")
col4, col5 = st.columns([2, 1])
with col4:
    selected_ranges = st.multiselect(
        "⏳ Forecast Horizon (Select One or More)",
        ["Next 7 Days", "Next 30 Days", "Next 90 Days"],
        default=["Next 30 Days"]
    )
with col5:
    safety_pct = st.slider("📦 Safety Stock %", min_value=0, max_value=100, value=20, step=5)

range_map = {
    "Next 7 Days": 7,
    "Next 30 Days": 30,
    "Next 90 Days": 90
}
forecast_days_list = [range_map[r] for r in selected_ranges]

if not forecast_days_list:
    st.warning("Please select at least one forecast horizon.")
    st.stop()

# ------------------ RUN FORECAST ------------------
st.markdown("### 🔮 SKU-Level Sales Forecast")
col_f1, col_f2 = st.columns([0.8, 0.2])
with col_f1:
    st.write("")

# Run for max required days (e.g., 90 if selected)
forecast_df = forecast_multiple_skus(
    df=filtered_df,
    sku_col='product_sku',
    date_col='order_date',
    qty_col='product_qty',
    forecast_days=max(forecast_days_list)
)

if forecast_df.empty:
    st.info("⚠️ No SKUs with sufficient historical data (≥30 days). Try different filters.")
    st.stop()

# Compute historical sales summary (last 7, 30, 120 days)
today = pd.to_datetime(df['order_date'].max())
hist_7d = filtered_df[filtered_df['order_date'] >= today - timedelta(days=6)].groupby('product_sku')['product_qty'].sum().rename("qty_last_7d")
hist_30d = filtered_df[filtered_df['order_date'] >= today - timedelta(days=29)].groupby('product_sku')['product_qty'].sum().rename("qty_last_30d")
hist_120d = filtered_df[filtered_df['order_date'] >= today - timedelta(days=119)].groupby('product_sku')['product_qty'].sum().rename("qty_last_120d")

# Build forecast pivot table
forecast_pivot = (
    forecast_df
    .groupby(['product_sku', 'forecast_days_ahead'])['forecast_qty']
    .sum()
    .reset_index()
    .pivot(index='product_sku', columns='forecast_days_ahead', values='forecast_qty')
    .fillna(0)
)

# Add forecast horizon columns dynamically
forecast_summary = pd.DataFrame(index=forecast_pivot.index)
for days in forecast_days_list:
    forecast_summary[f"forecast_qty_{days}d"] = forecast_pivot.loc[:, :days].sum(axis=1)

# Join historical columns
forecast_summary = forecast_summary.join([hist_7d, hist_30d, hist_120d])
forecast_summary.reset_index(inplace=True)
forecast_summary.fillna(0, inplace=True)

# Show final forecast summary table
with col_f2:
    forecast_csv = prepare_forecast_csv(forecast_summary)
    st.download_button(
        label="⬇️ Download CSV",
        data=forecast_csv,
        file_name="forecast_summary.csv",
        mime="text/csv",
        use_container_width=True
    )

st.dataframe(forecast_summary, use_container_width=True)

# ------------------ RECOMMENDED INVENTORY ------------------
st.markdown("### 🧮 Recommended Inventory Planning")
col_i1, col_i2 = st.columns([0.8, 0.2])
with col_i1:
    st.write("")

# Choose largest forecast horizon
best_col = f"forecast_qty_{max(forecast_days_list)}d"
rec_df = forecast_summary[['product_sku', best_col]].rename(columns={best_col: 'forecast_qty'})
rec_df['avg_daily_forecast'] = rec_df['forecast_qty'] / max(forecast_days_list)
rec_df['safety_stock'] = rec_df['avg_daily_forecast'] * (max(forecast_days_list) / 2) * (safety_pct / 100)
rec_df['recommended_inventory'] = rec_df['forecast_qty'] + rec_df['safety_stock']
rec_df['current_inventory'] = 100
rec_df['po_quantity'] = rec_df['recommended_inventory'] - rec_df['current_inventory']
rec_df['po_quantity'] = rec_df['po_quantity'].apply(lambda x: max(0, round(x)))

with col_i2:
    rec_csv = prepare_forecast_csv(rec_df)
    st.download_button(
        label="⬇️ Download CSV",
        data=rec_csv,
        file_name="inventory_recommendation.csv",
        mime="text/csv",
        use_container_width=True
    )

st.dataframe(
    rec_df[['product_sku', 'forecast_qty', 'recommended_inventory', 'current_inventory', 'po_quantity']],
    use_container_width=True
)
