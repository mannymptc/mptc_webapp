import streamlit as st
import pandas as pd
import pyodbc
from datetime import date, timedelta
from utils.db import connect_db

st.set_page_config(page_title="📋 Channel-wise Detailed Report", layout="wide")
st.title("🧾 Channel-wise Detailed Analytics")

@st.cache_data
def load_data():
    conn = connect_db()
    query = """
    SELECT order_id, order_channel, order_value, order_cust_postcode, product_sku, 
           product_name, product_qty, despatch_date
    FROM OrdersDespatch
    """
    return pd.read_sql(query, conn)

df = load_data()

channels = sorted(df['order_channel'].dropna().unique().tolist())
selected_channel = st.selectbox("📦 Select a Sales Channel", channels)

st.subheader(f"📦 Channel: `{selected_channel}`")
channel_df = df[df['order_channel'] == selected_channel]

selected_dates = st.date_input(f"Despatch Date Range for {selected_channel}", [], key=selected_channel)

if len(selected_dates) == 0:
    end_date = pd.to_datetime(date.today())
    start_date = end_date - timedelta(days=9)
elif len(selected_dates) == 1:
    start_date = end_date = pd.to_datetime(selected_dates[0])
else:
    start_date, end_date = pd.to_datetime(selected_dates)

channel_df = channel_df[channel_df['despatch_date'].between(start_date, end_date)]

if channel_df.empty:
    st.warning("No data for selected date range.")
else:
    dedup_orders = channel_df.drop_duplicates(subset='order_id')
    total_orders = dedup_orders['order_id'].nunique()
    total_revenue = dedup_orders['order_value'].sum()
    avg_order_value = dedup_orders['order_value'].mean()
    unique_skus = channel_df['product_sku'].nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🛒 Total Orders", total_orders)
    col2.metric("💰 Total Revenue", f"£ {total_revenue:,.2f}")
    col3.metric("📦 Avg Order Value", f"£ {avg_order_value:,.2f}")
    col4.metric("🔢 Unique SKUs Sold", unique_skus)

    sku_summary = channel_df.groupby(['product_sku', 'product_name']).agg(total_qty=('product_qty', 'sum')).reset_index()

    st.markdown("### 🔝 Top 5 Most Sold SKUs")
    st.dataframe(sku_summary.sort_values(by='total_qty', ascending=False).head(5))

    st.markdown("### 🔻 Bottom 5 Least Sold SKUs")
    st.dataframe(sku_summary.sort_values(by='total_qty', ascending=True).head(5))

    postcode_summary = channel_df['order_cust_postcode'].value_counts().reset_index()
    postcode_summary.columns = ['Postcode', 'Orders']

    if not postcode_summary.empty:
        st.markdown("### 🏡 Top 5 Most Common Postcodes")
        st.dataframe(postcode_summary.head(5))

        st.markdown("### 🏡 Top 5 Least Common Postcodes")
        st.dataframe(postcode_summary.tail(5).sort_values(by="Orders"))
    else:
        st.info("No postcode data available.")

    st.markdown("### 🧾 Sample Raw Data")
    st.dataframe(channel_df.head(10))

    csv_data = channel_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Full Channel Data as CSV",
        data=csv_data,
        file_name=f"{selected_channel.replace(' ', '_')}_Orders.csv",
        mime="text/csv"
    )
