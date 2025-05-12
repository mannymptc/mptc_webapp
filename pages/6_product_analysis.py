import streamlit as st
import pandas as pd
import pyodbc
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="📊 Product Sales Analysis", layout="wide")
st.title("📦 Product Sales History & Dead Stock")

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
        od.order_channel,
        od.order_date,
        od.product_qty,
        od.product_price
    FROM OrdersDespatch od
    LEFT JOIN Products p ON od.product_sku = p.product_sku
    WHERE od.order_date >= '2023-06-01'
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['sale_amount'] = df['product_qty'] * df['product_price']
    return df

df = load_data()
if df.empty:
    st.stop()

# ------------------ SIDEBAR DATE FILTER ------------------
st.sidebar.header("📅 Order Date Filter")
all_dates = df['order_date'].dt.normalize().dropna().unique()
selected_date_range = st.sidebar.date_input("Select Order Date Range", [min(all_dates), max(all_dates)])
start_date = pd.to_datetime(selected_date_range[0])
end_date = pd.to_datetime(selected_date_range[1])

# ------------------ TABS ------------------
tab1, tab2 = st.tabs(["📊 Sales History", "🧊 Unsold / Dead Stock"])

# ------------------ TAB 1: SALES HISTORY ------------------
with tab1:
    st.subheader("📈 Sales Summary")

    # ------------------ 1. Smart Search Filters ------------------
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

    # ------------------ 2. Apply Date Filter ------------------
    start_date = pd.to_datetime(selected_date_range[0])
    end_date = pd.to_datetime(selected_date_range[1])

    filtered_df = filtered_df[filtered_df['order_date'].between(start_date, end_date)]

    if filtered_df.empty:
        st.warning("No data available for selected filters.")
        st.stop()

    # ------------------ 3. KPIs ------------------
    days_range = (end_date - start_date).days + 1
    total_qty = filtered_df['product_qty'].sum()
    total_revenue = filtered_df['sale_amount'].sum()

    avg_qty_day = total_qty / days_range
    avg_rev_day = total_revenue / days_range
    avg_qty_week = avg_qty_day * 7
    avg_rev_week = avg_rev_day * 7
    avg_qty_month = avg_qty_day * 30
    avg_rev_month = avg_rev_day * 30

    col1, col2, col3 = st.columns(3)
    col1.metric("🔢 Total Quantity Sold", int(total_qty))
    col2.metric("💰 Total Revenue", f"£ {total_revenue:,.2f}")
    col3.metric("📅 Days Selected", f"{days_range} days")

    col4, col5, col6 = st.columns(3)
    col4.metric("📦 Avg Qty / Day", f"{avg_qty_day:.2f}")
    col5.metric("📦 Avg Qty / Week", f"{avg_qty_week:.2f}")
    col6.metric("📦 Avg Qty / Month", f"{avg_qty_month:.2f}")

    col7, col8, col9 = st.columns(3)
    col7.metric("💵 Avg Rev / Day", f"£ {avg_rev_day:.2f}")
    col8.metric("💵 Avg Rev / Week", f"£ {avg_rev_week:.2f}")
    col9.metric("💵 Avg Rev / Month", f"£ {avg_rev_month:.2f}")

    # ------------------ 5. Raw Data + Download ------------------
    row_col1, row_col2 = st.columns([0.8, 0.2])
    with row_col1:
        st.markdown("### 📃 Filtered Sales Data")
    with row_col2:
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            csv_data,
            file_name="filtered_sales.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    st.dataframe(filtered_df, use_container_width=True, height=500)

     # ------------------ 4. Channel-wise Summary ------------------
    st.markdown("### 📊 Channel-wise Sales Summary")
    channel_summary = (
        filtered_df.groupby('order_channel')
        .agg(
            total_orders=('order_id', pd.Series.nunique),
            total_qty=('product_qty', 'sum'),
            total_revenue=('sale_amount', 'sum')
        )
        .reset_index()
        .sort_values(by='total_revenue', ascending=False)
    )
    st.dataframe(channel_summary, use_container_width=True)

# ------------------ TAB 2: DEAD STOCK ------------------
with tab2:
    st.subheader("🧊 Dead or Unsold Stock")

    from dateutil.relativedelta import relativedelta
    import plotly.express as px

    # Get last sold date per product
    last_sold = df.groupby(['product_sku', 'product_name'])['order_date'].max().reset_index()
    last_sold['Days Since Last Sale'] = (pd.Timestamp.now().normalize() - last_sold['order_date']).dt.days
    last_sold['Last Sold'] = last_sold['order_date'].dt.strftime('%Y-%m-%d')

    # Human-readable "Time Since Last Sale"
    def time_since(date):
        delta = relativedelta(datetime.now().date(), date)
        parts = []
        if delta.years: parts.append(f"{delta.years} yr{'s' if delta.years > 1 else ''}")
        if delta.months: parts.append(f"{delta.months} mo")
        if delta.days: parts.append(f"{delta.days} d")
        return " ".join(parts) if parts else "Today"

    last_sold['Time Since Last Sale'] = pd.to_datetime(last_sold['order_date']).dt.date.apply(time_since)

    # Define ranges for unsold buckets (fixed display order)
    unsold_buckets = {
        "7 days to 1 month": (7, 30),
        "1 to 3 months": (31, 90),
        "3 to 6 months": (91, 180),
        "6 months to 1 year": (181, 365),
        "more than 1 year": (366, float("inf"))
    }

    # Assign each SKU to one bucket
    def assign_bucket(days):
        for bucket, (min_d, max_d) in unsold_buckets.items():
            if min_d <= days <= max_d:
                return bucket
        return None

    last_sold['Bucket'] = last_sold['Days Since Last Sale'].apply(assign_bucket)

    # ------------------ 1. Summary KPI for ALL Buckets ------------------
    st.markdown("### 📦 Unique SKU Count Unsold by Time Bucket")
    bucket_order = list(unsold_buckets.keys())
    bucket_counts = (
        last_sold.groupby('Bucket')['product_sku'].nunique()
        .reindex(bucket_order)
        .reset_index()
        .fillna(0)
    )
    bucket_counts.columns = ['Bucket', 'Unique SKU Count']
    kpi_cols = st.columns(len(bucket_counts))
    for i, row in bucket_counts.iterrows():
        kpi_cols[i].metric(label=row['Bucket'], value=f"{int(row['Unique SKU Count'])} SKUs")

    # ------------------ 2. Multiselect Filter (affects only table) ------------------
    selected_buckets = st.multiselect(
        "📅 Select Unsold Time Range(s) to View Data Table",
        options=bucket_order,
        default=["1 to 3 months"]
    )

    if not selected_buckets:
        st.warning("Please select at least one unsold duration to show the table.")
    else:
        # Filtered view for table only
        dead_stock = last_sold[last_sold['Bucket'].isin(selected_buckets)].copy()
        if dead_stock.empty:
            st.info("✅ No dead stock found for selected range(s).")
        else:
            # ------------------ 3. Data Table + Inline Download ------------------
            dead_stock_sorted = dead_stock.sort_values(by="Days Since Last Sale", ascending=True)

            row1_col1, row1_col2 = st.columns([0.8, 0.2])
            with row1_col1:
                st.markdown("### 🧾 Dead Stock List")
            with row1_col2:
                csv_dead = dead_stock_sorted.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Download CSV", csv_dead, file_name="dead_stock.csv", mime="text/csv", use_container_width=True)

            st.dataframe(
                dead_stock_sorted[['product_sku', 'product_name', 'Bucket', 'Last Sold', 'Days Since Last Sale', 'Time Since Last Sale']],
                use_container_width=True,
                height=500
            )

    # ------------------ 4. Charts (Bar + Box Side-by-Side) ------------------
    st.markdown("### 📊 Visual Summary of All Buckets")

    # Bar Chart: Count of SKUs per bucket (all)
    bar_fig = px.bar(
        bucket_counts,
        x="Bucket",
        y="Unique SKU Count",
        title="🧊 Unsold SKU Count by Time Bucket",
        text="Unique SKU Count"
    )
    bar_fig.update_traces(textposition="outside")
    bar_fig.update_layout(height=700)

    # Box Plot: Distribution of Days Since Last Sale per bucket (all)
    box_data = last_sold.dropna(subset=['Bucket'])
    box_fig = px.box(
        box_data,
        x="Bucket",
        y="Days Since Last Sale",
        points="all",
        title="📦 Days Since Last Sale Distribution by Time Bucket",
        color="Bucket",
        category_orders={"Bucket": [
            "7 days to 1 month",
            "1 to 3 months",
            "3 to 6 months",
            "6 months to 1 year",
            "more than 1 year"
        ]}
    )

    box_fig.update_layout(height=700)

    col1, col2 = st.columns(2)
    col1.plotly_chart(bar_fig, use_container_width=True)
    col2.plotly_chart(box_fig, use_container_width=True)

    # ------------------ 5. SKU Count by Product Category ------------------
    st.markdown("### 🧯 Unsold SKU Count by Product Category")

    # Join categories
    df_with_category = df.dropna(subset=['product_category'])
    sku_category_map = df_with_category[['product_sku', 'product_category']].drop_duplicates()
    dead_skus = pd.merge(last_sold.dropna(subset=['Bucket']), sku_category_map, on='product_sku', how='left')

    # Count by category
    category_counts = (
        dead_skus.groupby('product_category')['product_sku']
        .nunique()
        .reset_index()
        .rename(columns={'product_sku': 'Unsold SKU Count'})
        .sort_values(by='Unsold SKU Count', ascending=False)
    )

    st.dataframe(category_counts, use_container_width=True)

    fig_cat = px.bar(
        category_counts,
        x="product_category",
        y="Unsold SKU Count",
        title="📊 Unsold SKU Count by Product Category",
        text="Unsold SKU Count"
    )
    fig_cat.update_traces(textposition="outside")
    fig_cat.update_layout(xaxis_tickangle=-45, height=500)
    st.plotly_chart(fig_cat, use_container_width=True)
