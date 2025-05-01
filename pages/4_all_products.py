import streamlit as st
import pandas as pd
import pyodbc

st.set_page_config(page_title="📦 All Products", layout="wide")
st.title("📦 Products Information Portal")

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
    return pd.read_sql("SELECT * FROM Products", conn)

df = load_data()

st.markdown("### 🔍 Filter Products")
temp_df = df.copy()

# Filters
col1, col2, col3, col4 = st.columns(4)
with col1:
    skus = st.multiselect("Product SKU", sorted(temp_df['product_sku'].dropna().unique()))
with col2:
    categories = st.multiselect("Category", sorted(temp_df['product_category'].dropna().unique()))
with col3:
    names = st.multiselect("Product Name", sorted(temp_df['product_name'].dropna().unique()))
with col4:
    descriptions = st.multiselect("Description", sorted(temp_df['product_description'].dropna().unique()))

if skus:
    temp_df = temp_df[temp_df['product_sku'].isin(skus)]
if categories:
    temp_df = temp_df[temp_df['product_category'].isin(categories)]
if names:
    temp_df = temp_df[temp_df['product_name'].isin(names)]
if descriptions:
    temp_df = temp_df[temp_df['product_description'].isin(descriptions)]

st.subheader("📄 Product Records")
st.dataframe(temp_df if not temp_df.empty else df.head(10), use_container_width=True)

if not temp_df.empty:
    csv = temp_df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download as CSV", data=csv, file_name="filtered_products.csv", mime="text/csv")
