import streamlit as st
import pandas as pd
import pyodbc
from datetime import datetime
import plotly.express as px
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

st.set_page_config(page_title="📦 Channel Despatch Summary", layout="wide")
st.title("🚚 Daily Despatch Summary")

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
def load_data(start_date_str=None, end_date_str=None):
    if start_date_str and end_date_str:
        date_filter = f"WHERE CAST(despatch_date AS DATE) >= '{start_date_str}' AND CAST(despatch_date AS DATE) <= '{end_date_str}'"
    else:
        date_filter = ""

    query = f"""
    WITH despatch_data AS (
        SELECT DISTINCT order_id, order_channel, despatch_date, order_value
        FROM OrdersDespatch
        {date_filter}
    ),
    channel_total AS (
        SELECT 
            order_channel, 
            SUM(order_value) AS total_orders_value,
            COUNT(DISTINCT order_id) AS orders_count
        FROM despatch_data
        GROUP BY order_channel
    )
    SELECT
        order_channel AS channel,
        total_orders_value,
        orders_count
    FROM channel_total
    ORDER BY total_orders_value DESC;
    """

    try:
        conn = connect_db()
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return pd.DataFrame()

# ------------------ SIDEBAR DATE FILTER ------------------
st.sidebar.header("Select Despatch Date Range")
selected_range = st.sidebar.date_input("Despatch Date Range", [])

if len(selected_range) == 1:
    start_date = end_date = selected_range[0]
elif len(selected_range) == 2:
    start_date, end_date = selected_range
else:
    start_date = end_date = None

start_date_str = start_date.strftime("%Y-%m-%d") if start_date else None
end_date_str = end_date.strftime("%Y-%m-%d") if end_date else None

# ------------------ LOAD DATA ------------------
df = load_data(start_date_str, end_date_str)

if df.empty:
    st.warning("No orders found for the selected despatch date(s).")
    st.stop()

# ------------------ GRAND TOTAL ------------------
grand_total_value = df["total_orders_value"].sum()
grand_total_count = df["orders_count"].sum()
df.loc[len(df.index)] = ["Grand Total", grand_total_value, grand_total_count]

# ------------------ CREATE EXCEL FILE ------------------
output = io.BytesIO()
wb = Workbook()
ws = wb.active
ws.title = "Channel Summary"

ws["A1"] = "Selected Despatch Date:"
if start_date and end_date:
    ws["B1"] = start_date.strftime("%d-%m-%Y") if start_date == end_date else f"{start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}"
else:
    ws["B1"] = "All Available Dates"

ws["A2"] = "Day:"
if start_date and end_date:
    ws["B2"] = start_date.strftime("%A") if start_date == end_date else "Multiple Days"
else:
    ws["B2"] = "All Days"

ws["A1"].font = Font(bold=True)
ws["A2"].font = Font(bold=True)

rows = dataframe_to_rows(df, index=False, header=True)
for r_idx, row in enumerate(rows, 4):
    for c_idx, value in enumerate(row, 1):
        cell = ws.cell(row=r_idx, column=c_idx, value=value)
        if r_idx == 4 or row[0] == "Grand Total":
            cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")
        cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

ws.column_dimensions["A"].width = 30
ws.column_dimensions["B"].width = 20
ws.column_dimensions["C"].width = 15

wb.save(output)
output.seek(0)

# ------------------ HEADER + DOWNLOAD BUTTON ------------------
left_col, right_col = st.columns([6, 1])

with left_col:
    if start_date and end_date:
        if start_date == end_date:
            st.subheader(f"📋 Channel Summary for {start_date.strftime('%Y-%m-%d')} ({start_date.strftime('%A')})")
        else:
            st.subheader(f"📋 Channel Summary from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    else:
        st.subheader("📋 Channel Summary for All Dates")

with right_col:
    file_name = f"Channel_Summary_{start_date_str or 'All'}_to_{end_date_str or 'All'}.xlsx"
    st.download_button(
        label="📅 Download Excel",
        data=output,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ------------------ SHOW TABLE ------------------
st.dataframe(df, use_container_width=True)

# ------------------ CHARTS ------------------
df_chart = df[df["channel"] != "Grand Total"]

st.subheader("📊 Total Orders Value by Channel")
fig_value_bar = px.bar(df_chart, x="channel", y="total_orders_value", text="total_orders_value", title="Channel-wise Total Order Value")
st.plotly_chart(fig_value_bar, use_container_width=True)

st.subheader("📦 Orders Count by Channel")
fig_count_bar = px.bar(df_chart, x="channel", y="orders_count", text="orders_count", title="Channel-wise Orders Count")
st.plotly_chart(fig_count_bar, use_container_width=True)

st.subheader("🍩 Revenue Share by Channel")
fig_donut_value = px.pie(df_chart, names='channel', values='total_orders_value', title='Revenue Share', hole=0.4)
st.plotly_chart(fig_donut_value, use_container_width=True)

st.subheader("🍩 Orders Count Share by Channel")
fig_donut_count = px.pie(df_chart, names='channel', values='orders_count', title='Orders Count Share', hole=0.4)
st.plotly_chart(fig_donut_count, use_container_width=True)
