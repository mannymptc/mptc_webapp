import streamlit as st
import pandas as pd
import pyodbc
import io
from openpyxl import Workbook
from datetime import datetime

st.set_page_config(page_title="📦 Channel Despatch Summary", layout="wide")
st.title("🚚 Daily Despatch Summary")

def connect_db():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=mptcecommerce-sql-server.database.windows.net;"
        "DATABASE=mptcecommerce-db;"
        "UID=mptcadmin;"
        "PWD=Mptc@2025"
    )

conn = connect_db()

def load_data(start_date_str=None, end_date_str=None):
    date_filter = f"WHERE CAST(despatch_date AS DATE) BETWEEN '{start_date_str}' AND '{end_date_str}'" if start_date_str and end_date_str else ""
    query = f"""
    WITH despatch_data AS (
        SELECT DISTINCT order_id, order_channel, despatch_date, order_value
        FROM OrdersDespatch
        {date_filter}
    )
    SELECT order_channel AS channel, SUM(order_value) AS total_orders_value, COUNT(DISTINCT order_id) AS orders_count
    FROM despatch_data
    GROUP BY order_channel
    ORDER BY total_orders_value DESC
    """
    return pd.read_sql(query, conn)

st.sidebar.header("Select Despatch Date Range")
selected_range = st.sidebar.date_input("Despatch Date Range", [])

start_date_str, end_date_str = None, None
if len(selected_range) == 1:
    start_date_str = end_date_str = selected_range[0].strftime("%Y-%m-%d")
elif len(selected_range) == 2:
    start_date_str, end_date_str = selected_range[0].strftime("%Y-%m-%d"), selected_range[1].strftime("%Y-%m-%d")

df = load_data(start_date_str, end_date_str)
df.loc[len(df.index)] = ["Grand Total", df["total_orders_value"].sum(), df["orders_count"].sum()]

st.dataframe(df, use_container_width=True)

output = io.BytesIO()
wb = Workbook()
ws = wb.active
ws.title = "Channel Summary"

for r_idx, row in enumerate(df.itertuples(index=False), 1):
    for c_idx, value in enumerate(row, 1):
        ws.cell(row=r_idx, column=c_idx).value = value

wb.save(output)
output.seek(0)

st.download_button("📅 Download Excel", data=output, file_name="Channel_Summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

fig = px.bar(df[df["channel"] != "Grand Total"], x="channel", y="total_orders_value", text="total_orders_value")
st.plotly_chart(fig, use_container_width=True)
