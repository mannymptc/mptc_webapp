st.sidebar.header("📅 Filter by Date")

# --- Manual Inputs ---
order_date_range = st.sidebar.date_input("Order Date Range", [])
despatch_date_range = st.sidebar.date_input("Despatch Date Range", [])

# --- Quick Filters ---
order_quick = st.sidebar.selectbox("🕒 Quick Order Date Range", [
    "None", "Yesterday", "Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "Last 12 Months"
])
despatch_quick = st.sidebar.selectbox("🕒 Quick Despatch Date Range", [
    "None", "Yesterday", "Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "Last 12 Months"
])

# --- Helper Function ---
def get_range_from_option(option, available_dates):
    if len(available_dates) == 0:
        return None, None
    today = max(available_dates)

    if option == "Yesterday":
        return today, today
    elif option == "Last 7 Days":
        return today - timedelta(days=6), today
    elif option == "Last 30 Days":
        return today - timedelta(days=29), today
    elif option == "Last 3 Months":
        return today - relativedelta(months=3), today
    elif option == "Last 6 Months":
        return today - relativedelta(months=6), today
    elif option == "Last 12 Months":
        return today - relativedelta(months=12), today
    else:
        return None, None

# --- Determine Date Ranges from Data ---
order_dates = sorted(df['order_date'].dropna().unique())
despatch_dates = sorted(df['despatch_date'].dropna().unique())

# --- Final Order Date Range ---
if order_quick != "None":
    order_start, order_end = get_range_from_option(order_quick, order_dates)
elif len(order_date_range) == 1:
    order_start = order_end = pd.to_datetime(order_date_range[0])
elif len(order_date_range) == 2:
    order_start, order_end = pd.to_datetime(order_date_range)
else:
    order_start, order_end = min(order_dates), max(order_dates)  # <- FIX: use full range as fallback

# --- Final Despatch Date Range ---
if despatch_quick != "None":
    despatch_start, despatch_end = get_range_from_option(despatch_quick, despatch_dates)
elif len(despatch_date_range) == 1:
    despatch_start = despatch_end = pd.to_datetime(despatch_date_range[0])
elif len(despatch_date_range) == 2:
    despatch_start, despatch_end = pd.to_datetime(despatch_date_range)
else:
    despatch_start, despatch_end = min(despatch_dates), max(despatch_dates)  # <- FIX

# --- Debugging Output ---
st.caption(f"🗓️ Order Filter Range: {order_start.date()} to {order_end.date()}")
st.caption(f"🗓️ Despatch Filter Range: {despatch_start.date()} to {despatch_end.date()}")
