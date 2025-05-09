import streamlit as st
import pandas as pd
import pyodbc
from datetime import date, timedelta

st.set_page_config(page_title="📋 Channel-wise Detailed Report", layout="wide")
st.title("🧾 Channel-wise Detailed Analytics")

# ------------------ DATABASE CONNECTION ------------------
def connect_db():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=mptcecommerce-sql-server.database.windows.net;"
        "DATABASE=mptcecommerce-db;"
        "UID=mptcadmin;"
        "PWD=Mptc@2025"
    )

# ------------------ LOAD DATA FUNCTION ------------------
@st.cache_data
def load_data():
    try:
        conn = connect_db()
        query = """
        SELECT order_id, order_channel, order_value, order_cust_postcode, product_sku, 
               product_name, product_qty, product_price, despatch_date
        FROM OrdersDespatch
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return pd.DataFrame()

# ------------------ MAIN LOGIC ------------------
df = load_data()
if df.empty:
    st.stop()

# ------------------ CHANNEL FILTER ------------------
channels = sorted(df['order_channel'].dropna().unique().tolist())
all_option = "Select All"
channels_with_all = [all_option] + channels

selected_channels = st.multiselect("📦 Select Sales Channel(s)", options=channels_with_all, default=all_option)

# Logic for 'Select All'
if all_option in selected_channels:
    selected_channels = channels  # Use all real channels

filtered_df = df[df['order_channel'].isin(selected_channels)]

# ------------------ DATE RANGE FILTER ------------------
selected_dates = st.date_input("Despatch Date Range", [])

if len(selected_dates) == 0:
    end_date = pd.to_datetime(date.today())
    start_date = end_date - timedelta(days=9)
elif len(selected_dates) == 1:
    start_date = end_date = pd.to_datetime(selected_dates[0])
else:
    start_date, end_date = pd.to_datetime(selected_dates)

filtered_df = filtered_df[filtered_df['despatch_date'].between(start_date, end_date)]

if filtered_df.empty:
    st.warning("No data for selected filters.")
    st.stop()

# ------------------ TOP N DROPDOWN ------------------
top_n = st.selectbox("Show Top/Bottom N Records", [5, 10, 15, 20, 25], index=1)

# ------------------ KPIs ------------------
dedup_orders = filtered_df.drop_duplicates(subset='order_id')
total_orders = dedup_orders['order_id'].nunique()
total_revenue = dedup_orders['order_value'].sum()
avg_order_value = dedup_orders['order_value'].mean()
unique_skus = filtered_df['product_sku'].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("🛒 Total Orders", total_orders)
col2.metric("💰 Total Revenue", f"£ {total_revenue:,.2f}")
col3.metric("📦 Avg Order Value", f"£ {avg_order_value:,.2f}")
col4.metric("🔢 Unique SKUs Sold", unique_skus)

# ------------------ SKU SUMMARY ------------------
# Use deduplication based on order_id for SKU aggregation
dedup_df = filtered_df.drop_duplicates(subset=["order_id", "product_sku"])

sku_summary = (
    dedup_df.groupby(['product_sku', 'product_name'])
    .agg(
        sold_qty=('product_qty', 'sum'),
        revenue=('product_price', lambda x: (x * dedup_df.loc[x.index, 'product_qty']).sum())
    )
    .reset_index()
)

# ------------------ TOP / BOTTOM SKU TABLES ------------------
st.markdown(f"### 🔝 Top {top_n} Most Sold SKUs")
st.dataframe(
    sku_summary.sort_values(by='sold_qty', ascending=False)
    .head(top_n)[['product_sku', 'product_name', 'sold_qty', 'revenue']],
    use_container_width=True
)

st.markdown(f"### 🔻 Bottom {top_n} Least Sold SKUs")
st.dataframe(
    sku_summary.sort_values(by='sold_qty', ascending=True)
    .head(top_n)[['product_sku', 'product_name', 'sold_qty', 'revenue']],
    use_container_width=True
)

# ------------------ POSTCODE STATS ------------------
postcode_summary = filtered_df['order_cust_postcode'].value_counts().reset_index()
postcode_summary.columns = ['Postcode', 'Orders']

if not postcode_summary.empty:
    st.markdown(f"### 🏡 Top {top_n} Most Common Postcodes")
    st.dataframe(postcode_summary.head(top_n), use_container_width=True)

    st.markdown(f"### 🏡 Top {top_n} Least Common Postcodes")
    st.dataframe(postcode_summary.tail(top_n).sort_values(by="Orders"), use_container_width=True)
else:
    st.info("No postcode data available.")

# ------------------ RAW DATA + DOWNLOAD ------------------
st.markdown("### 🧾 Sample Raw Data")
st.dataframe(filtered_df.head(10), use_container_width=True)

csv_data = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download Full Filtered Channel Data as CSV",
    data=csv_data,
    file_name=f"filtered_channel_orders.csv",
    mime="text/csv"
)
