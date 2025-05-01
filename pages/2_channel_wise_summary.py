import streamlit as st
import pandas as pd
import pyodbc
from datetime import datetime
import plotly.express as px
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from utils.db import connect_db

st.set_page_config(page_title="📦 Channel Despatch Summary", layout="wide")
st.title("🚚 Daily Despatch Summary")

# ------------------ DATABASE CONNECTION ------------------
def load_data(start_date_str=None, end_date_str=None):
    try:
        conn = connect_db()
        if start_date_str and end_date_str:
            date_filter = f"WHERE CAST(despatch_date AS DATE) BETWEEN '{start_date_str}' AND '{end_date_str}'"
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
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# ------------------ USER INPUT ------------------
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
    st.warning("No orders found for selected date(s).")
    st.stop()

grand_total_value = df["total_orders_value"].sum()
grand_total_count = df["orders_count"].sum()
df.loc[len(df.index)] = ["Grand Total", grand_total_value, grand_total_count]

# ------------------ CREATE EXCEL ------------------
df_export = df.copy()
output = io.BytesIO()
wb = Workbook()
ws = wb.active
ws.title = "Channel Summary"

ws["A1"] = "Selected Despatch Date:"
ws["B1"] = f"{start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}" if start_date and end_date else "All Available Dates"
ws["A2"] = "Day:"
ws["B2"] = start_date.strftime("%A") if start_date else "All Days"

ws["A1"].font = ws["A2"].font = Font(bold=True)

rows = dataframe_to_rows(df_export, index=False, header=True)
for r_idx, row in enumerate(rows, 4):
    for c_idx, value in enumerate(row, 1):
        cell = ws.cell(row=r_idx, column=c_idx, value=value)
        if r_idx == 4 or row[0] == "Grand Total":
            cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")
        cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

ws.column_dimensions["A"].width = 30
wb.save(output)
output.seek(0)

st.download_button(
    label="📅 Download Excel",
    data=output,
    file_name="Channel_Summary.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.dataframe(df, use_container_width=True, height=600)

# ------------------ CHARTS ------------------
df_chart = df[df["channel"] != "Grand Total"]

if not df_chart.empty:
    st.subheader("📊 Total Orders Value by Channel")
    fig = px.bar(df_chart, x="channel", y="total_orders_value",_
