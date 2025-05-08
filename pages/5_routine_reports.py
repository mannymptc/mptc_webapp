import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="📊 Routine Reports", layout="wide")
st.title("📊 Routine Reports Suite")

tab1, tab2 = st.tabs(["🧾 Channel-wise Invoices", "🔄 Mintsoft vs Opera Delta Report"])

# --- Channel-wise Invoice
with tab1:
    st.title("📦 Channel-wise SKU Invoices")
    uploaded_file = st.file_uploader("Upload Channel-wise Invoice file", type=["xlsx", "csv"])

    if uploaded_file:
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)

        # ✅ FIX: Clean column names
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        st.dataframe(df.head())
        channel_col = df.columns[0]
        channels = df[channel_col].unique()

        col_layout = st.columns(2)

        for idx, channel in enumerate(channels):
            filtered_df = df[df[channel_col] == channel]

            # ✅ Now this will NOT fail because column names are clean
            summary = filtered_df.groupby("product_sku").agg(
                total_qty=('product_qty', 'sum'),
                total_value=('order_value', 'sum')
            ).reset_index()

            with col_layout[idx % 2]:
                st.subheader(f"🔹 Channel: {channel}")
                st.dataframe(summary, use_container_width=True)

                csv = summary.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download CSV", data=csv, file_name=f"{channel}_summary.csv", mime='text/csv')

# --- Mintsoft vs Opera Delta
with tab2:
    st.title("🔄 Delta Report: Mintsoft vs Opera Stock")

    col1, col2 = st.columns(2)
    with col1:
        opera_file = st.file_uploader("Upload Opera Stock (.xlsx)", type=["xlsx"])
    with col2:
        mintsoft_file = st.file_uploader("Upload Mintsoft Export (.xlsx)", type=["xlsx"])

    if opera_file and mintsoft_file:
        opera_df = pd.read_excel(opera_file)
        mintsoft_df = pd.read_excel(mintsoft_file)

        opera_df = opera_df[['SKU', 'Free Stock Quantity']].rename(columns={'Free Stock Quantity': 'Opera_Stock'})
        mintsoft_df = mintsoft_df[['ProductSKU', 'Location', 'Quantity']].rename(columns={'ProductSKU': 'SKU', 'Quantity': 'Mintsoft_Quantity'})

        opera_df['SKU'] = opera_df['SKU'].astype(str)
        mintsoft_df['SKU'] = mintsoft_df['SKU'].astype(str)

        mintsoft_total = mintsoft_df.groupby('SKU')['Mintsoft_Quantity'].sum().reset_index()
        merged = opera_df.merge(mintsoft_total, on='SKU', how='inner')
        merged['Delta_Stock'] = merged['Opera_Stock'] - merged['Mintsoft_Quantity']

        st.subheader("📌 Delta Stock")
        st.dataframe(merged)

        csv = merged.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", data=csv, file_name="delta_stock.csv", mime="text/csv")
