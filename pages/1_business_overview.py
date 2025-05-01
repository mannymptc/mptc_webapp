import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px

st.set_page_config(page_title="📊 MPTC Business Dashboard", layout="wide")
st.title("🏭 Channel-wise Overview Dashboard")

# Database Connection
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
    SELECT order_id, order_channel, order_date, despatch_date, order_value, 
           order_cust_postcode, product_sku, product_name, product_qty, customer_name, 
           product_price, order_courier_service
    FROM OrdersDespatch
    """
    return pd.read_sql(query, conn)

df = load_data()
df['order_date'] = pd.to_datetime(df['order_date'])
df['despatch_date'] = pd.to_datetime(df['despatch_date'])

# Filters
st.sidebar.header("Filter Data")
channels = df['order_channel'].dropna().unique().tolist()
selected_channels = st.sidebar.multiselect("Select Channels", options=channels, default=channels)
order_date_range = st.sidebar.date_input("Filter by Order Date", [])
despatch_date_range = st.sidebar.date_input("Filter by Despatch Date", [])

df = df[df['order_channel'].isin(selected_channels)]

if len(order_date_range) == 1:
    df = df[df['order_date'].dt.date == order_date_range[0]]
elif len(order_date_range) == 2:
    df = df[df['order_date'].between(pd.to_datetime(order_date_range[0]), pd.to_datetime(order_date_range[1]))]

if len(despatch_date_range) == 1:
    df = df[df['despatch_date'].dt.date == despatch_date_range[0]]
elif len(despatch_date_range) == 2:
    df = df[df['despatch_date'].between(pd.to_datetime(despatch_date_range[0]), pd.to_datetime(despatch_date_range[1]))]

dedup_orders = df.drop_duplicates(subset='order_id')

total_orders = dedup_orders['order_id'].nunique()
total_revenue = dedup_orders['order_value'].sum()
avg_order_value = dedup_orders['order_value'].mean()
unique_product_skus = df['product_sku'].nunique()
total_quantity_ordered = df['product_qty'].sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🛒 Total Orders", total_orders)
col2.metric("💰 Total Revenue", f"£ {total_revenue:,.2f}")
col3.metric("📦 Avg Order Value", f"£ {avg_order_value:,.2f}")
col4.metric("🔢 Unique SKUs", unique_product_skus)
col5.metric("📦 Total Quantity Ordered", total_quantity_ordered)

# Charts
st.subheader("📈 Revenue Trend Over Time")
df_line = dedup_orders.groupby('order_date')['order_value'].sum().reset_index()
fig_line = px.line(df_line, x='order_date', y='order_value', title="Order Value Over Time")
st.plotly_chart(fig_line, use_container_width=True)

channel_summary = dedup_orders.groupby('order_channel').agg(
    total_orders_value=('order_value', 'sum'),
    orders_count=('order_id', 'nunique')
).reset_index()

st.subheader("📊 Total Orders Value by Channel")
fig = px.bar(channel_summary, x="order_channel", y="total_orders_value", text="total_orders_value")
st.plotly_chart(fig, use_container_width=True)

st.subheader("📦 Orders Count by Channel")
fig = px.bar(channel_summary, x="order_channel", y="orders_count", text="orders_count")
st.plotly_chart(fig, use_container_width=True)

st.subheader("🍩 Revenue Share by Channel")
fig = px.pie(channel_summary, names='order_channel', values='total_orders_value', hole=0.4)
st.plotly_chart(fig, use_container_width=True)

st.subheader("🍩 Orders Count Share by Channel")
fig = px.pie(channel_summary, names='order_channel', values='orders_count', hole=0.4)
st.plotly_chart(fig, use_container_width=True)
