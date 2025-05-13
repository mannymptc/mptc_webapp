import pandas as pd
from prophet import Prophet
from prophet.make_holidays import make_holidays_df
import warnings

warnings.filterwarnings("ignore")

def forecast_multiple_skus(df, sku_col, date_col, qty_col, forecast_days=30):
    forecast_results = []
    uk_holidays = make_holidays_df(year_list=[2023, 2024, 2025], country='UK')

    for sku in df[sku_col].unique():
        sku_df = df[df[sku_col] == sku].copy()
        if sku_df[date_col].nunique() < 30:
            continue

        daily_data = (
            sku_df.groupby(date_col)[qty_col]
            .sum()
            .reset_index()
            .rename(columns={date_col: 'ds', qty_col: 'y'})
        )

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            holidays=uk_holidays
        )
        model.fit(daily_data)

        future = model.make_future_dataframe(periods=forecast_days)
        forecast = model.predict(future)

        forecast_trimmed = forecast[['ds', 'yhat']].copy()
        forecast_trimmed['product_sku'] = sku
        forecast_trimmed['forecast_days_ahead'] = (forecast_trimmed['ds'] - pd.to_datetime(df[date_col].max())).dt.days
        forecast_trimmed = forecast_trimmed[forecast_trimmed['forecast_days_ahead'] > 0]

        forecast_results.append(forecast_trimmed)

    if not forecast_results:
        return pd.DataFrame()

    all_forecasts = pd.concat(forecast_results, ignore_index=True)
    all_forecasts.rename(columns={'ds': 'forecast_date', 'yhat': 'forecast_qty'}, inplace=True)
    return all_forecasts[['product_sku', 'forecast_date', 'forecast_qty']]

def prepare_forecast_csv(forecast_df):
    return forecast_df.to_csv(index=False).encode("utf-8")
