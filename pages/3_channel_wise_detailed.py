import streamlit as st
import pandas as pd
import pyodbc
from datetime import date, timedelta

st.set_page_config(page_title="📋 Channel-wise Detailed Report", layout="wide")
st.title("🧾 Channel-wise Detailed Analytics")

def connect_db():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=mptcecommerce-sql-server.database.windows.net;"
        "DATABASE=mptcecommerce-db;"
        "UID=mptcadmin;"
        "PWD=Mptc@2025"
    )

conn = connect_db()

@st.cache_data
def load_data():
    query = """
    SELECT order_id, order_channel, order_value, order_cust_postcode, 
           product_sku, product_name, product_qty, despatch_date
    FROM OrdersDespatch
    """
    return pd.read_sql(query, conn)

df = load_data()

channels = df['order_channel'].dropna().unique().tolist()
tabs = st.tabs(channels)

for tab, channel in zip(tabs, channels):
    with tab:
        st.subheader(f"📦 Channel: {channel}")

        channel_df = df[df['order_channel'] == channel]

        st.markdown("### 📅 Filter by Despatch Date")
        selected_dates = st.date_input(f"Despatch Date Range for {channel}", [], key=channel)

        if len(selected_dates) == 0:
            end_date = pd.to_datetime(date.today())
            start_date = end_date - timedelta(days=9)
            channel_df = channel_df[channel_df['despatch_date'].between(start_date, end_date)]
            st.info(f"Showing last 10 days")
        elif len(selected_dates) == 1:
            channel_df = channel_df[channel_df['despatch_date'].dt.date == selected_dates[0]]
        elif len(selected_dates) == 2:
            channel_df = channel_df[channel_df['despatch_date'].between(pd.to_datetime(selected_dates[0]), pd.to_datetime(selected_dates[1]))]

        if channel_df.empty:
            st.warning("No data found for selected range.")
            continue

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
        most_sold = sku_summary.sort_values(by='total_qty', ascending=False).head(5)
        least_sold = sku_summary.sort_values(by='total_qty', ascending=True).head(5)

        st.markdown("### 🔝 Top 5 Most Sold SKUs")
        st.dataframe(most_sold, use_container_width=True)

        st.markdown("### 🔻 Bottom 5 Least Sold SKUs")
        st.dataframe(least_sold, use_container_width=True)

        postcode_summary = channel_df['order_cust_postcode'].value_counts().reset_index()
        postcode_summary.columns = ['Postcode', 'Orders']

        if not postcode_summary.empty:
            st.markdown("### 🏡 Top 5 Most Common Postcodes")
            st.dataframe(postcode_summary.head(5), use_container_width=True)

            st.markdown("### 🏡 Top 5 Least Common Postcodes")
            st.dataframe(postcode_summary.tail(5).sort_values(by="Orders"), use_container_width=True)

        st.markdown("### 🧾 Sample Raw Data")
        st.dataframe(channel_df.head(10), use_container_width=True)

        csv_data = channel_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Full Channel Data as CSV", data=csv_data, file_name=f"{channel.replace(' ', '_')}_Orders.csv", mime="text/csv")
