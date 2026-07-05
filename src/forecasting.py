"""
XGBoost Sales Forecasting pipeline.
Trains a model on engineered Gold features and generates a recursive 30-day forecast.
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.config import settings
from src.logger import logger


def load_gold_data_to_pandas() -> pd.DataFrame:
    """Loads the Gold forecasting input Delta table into a Pandas DataFrame."""
    gold_path = settings.gold_dir / "gold_forecasting_input"
    logger.info(f"Loading Gold forecasting data from: {gold_path}")
    df_pandas = pd.read_parquet(str(gold_path))

    # Ensure date column is datetime format and sort
    df_pandas["date"] = pd.to_datetime(df_pandas["date"])
    df_pandas = df_pandas.sort_values(by=["id", "date"]).reset_index(drop=True)
    return df_pandas


def train_forecasting_model(df: pd.DataFrame) -> tuple[xgb.XGBRegressor, dict]:
    """Splits data chronologically, trains XGBoost, and evaluates performance."""
    logger.info("Preparing datasets for model training...")

    # Select features and target
    features = [
        "sell_price",
        "wday",
        "month",
        "year",
        "is_weekend",
        "is_holiday",
        "snap_CA",
        "snap_TX",
        "snap_WI",
        "lag_7",
        "lag_14",
        "lag_28",
        "rolling_7_avg",
        "rolling_30_avg",
    ]
    target = "sales"

    # Verify column presence
    missing_cols = [c for c in features + [target] if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in input DataFrame: {missing_cols}")

    # Chronological Split (reserve the last 30 days of data for evaluation)
    max_date = df["date"].max()
    split_date = max_date - pd.Timedelta(days=30)

    train_data = df[df["date"] <= split_date]
    val_data = df[df["date"] > split_date]

    X_train, y_train = train_data[features], train_data[target]
    X_val, y_val = val_data[features], val_data[target]

    logger.info(f"Train set: {X_train.shape[0]} rows, Validation set: {X_val.shape[0]} rows.")

    # Train XGBoost Regressor
    logger.info("Training XGBoost Regressor model...")
    model = xgb.XGBRegressor(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    # Evaluate model
    y_pred = model.predict(X_val)
    # Clip predictions to 0 since sales cannot be negative
    y_pred = np.clip(y_pred, 0, None)

    rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))
    mae = float(mean_absolute_error(y_val, y_pred))
    r2 = float(r2_score(y_val, y_pred))

    metrics = {"rmse": rmse, "mae": mae, "r2": r2}
    logger.info(f"Evaluation Metrics - RMSE: {rmse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}")

    # Retrain on the entire dataset to capture the latest patterns for forecasting
    logger.info("Retraining XGBoost model on full historical dataset...")
    full_model = xgb.XGBRegressor(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    full_model.fit(df[features], df[target], verbose=False)

    # Save model
    model_path = settings.models_dir / "xgboost_forecaster.joblib"
    logger.info(f"Saving trained model to: {model_path}")
    joblib.dump(full_model, model_path)

    return full_model, metrics


def generate_30day_forecast(df_hist: pd.DataFrame, model: xgb.XGBRegressor) -> pd.DataFrame:
    """Generates a recursive 30-day daily sales forecast for each product-store series."""
    logger.info("Initializing recursive 30-day forecasting...")

    # Read calendar for future dates (days 366 to 395)
    calendar_path = settings.raw_dir / "calendar.csv"
    calendar_df = pd.read_csv(calendar_path)
    calendar_df["date"] = pd.to_datetime(calendar_df["date"])

    # Determine historical max date
    max_hist_date = df_hist["date"].max()

    # Filter calendar to include only future dates
    future_calendar = calendar_df[calendar_df["date"] > max_hist_date].sort_values("date")
    future_dates = future_calendar["date"].unique()[:30]  # Target next 30 days

    # We will build a recursive data frame starting from history
    # Keep only columns we need to build lags and rollings
    cols_to_keep = [
        "id",
        "date",
        "item_id",
        "dept_id",
        "cat_id",
        "store_id",
        "state_id",
        "sell_price",
        "sales",
    ]
    df_recursive = df_hist[cols_to_keep].copy()

    # Pre-calculate prices per series (use last known price)
    last_prices = df_hist.groupby("id")["sell_price"].last().to_dict()

    # Get active series information
    series_info = df_hist[["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]].drop_duplicates()

    # Run daily prediction recursively
    for day_dt in future_dates:
        day_str = pd.to_datetime(day_dt).strftime("%Y-%m-%d")
        logger.info(f"Forecasting sales for date: {day_str}")

        # Fetch calendar attributes for this day
        cal_row = calendar_df[calendar_df["date"] == day_dt].iloc[0]

        # Build records for this day for all series
        day_records = []
        for _, row in series_info.iterrows():
            series_id = row["id"]
            state_id = row["state_id"]

            # Lags (relative to current day_dt)
            lag_7_date = day_dt - pd.Timedelta(days=7)
            lag_14_date = day_dt - pd.Timedelta(days=14)
            lag_28_date = day_dt - pd.Timedelta(days=28)

            def get_sales_at_date(sid, dt):
                match = df_recursive[(df_recursive["id"] == sid) & (df_recursive["date"] == dt)]
                return float(match["sales"].values[0]) if not match.empty else 0.0

            lag_7 = get_sales_at_date(series_id, lag_7_date)
            lag_14 = get_sales_at_date(series_id, lag_14_date)
            lag_28 = get_sales_at_date(series_id, lag_28_date)

            # Rolling averages (past 7 days and past 30 days)
            hist_series = df_recursive[df_recursive["id"] == series_id]

            r7_series = hist_series[(hist_series["date"] < day_dt) & (hist_series["date"] >= day_dt - pd.Timedelta(days=7))]
            rolling_7_avg = float(r7_series["sales"].mean()) if not r7_series.empty else 0.0

            r30_series = hist_series[(hist_series["date"] < day_dt) & (hist_series["date"] >= day_dt - pd.Timedelta(days=30))]
            rolling_30_avg = float(r30_series["sales"].mean()) if not r30_series.empty else 0.0

            sell_price = last_prices.get(series_id, 1.99)

            day_records.append({
                "id": series_id,
                "date": day_dt,
                "item_id": row["item_id"],
                "dept_id": row["dept_id"],
                "cat_id": row["cat_id"],
                "store_id": row["store_id"],
                "state_id": state_id,
                "sell_price": sell_price,
                # Features for model inference
                "wday": int(cal_row["wday"]),
                "month": int(cal_row["month"]),
                "year": int(cal_row["year"]),
                "is_weekend": 1 if int(cal_row["wday"]) in [1, 2] else 0,
                "is_holiday": 1 if cal_row["event_name_1"] and str(cal_row["event_name_1"]) != "nan" and cal_row["event_name_1"] != "" else 0,
                "snap_CA": int(cal_row["snap_CA"]),
                "snap_TX": int(cal_row["snap_TX"]),
                "snap_WI": int(cal_row["snap_WI"]),
                "lag_7": lag_7,
                "lag_14": lag_14,
                "lag_28": lag_28,
                "rolling_7_avg": rolling_7_avg,
                "rolling_30_avg": rolling_30_avg,
            })

        # Convert day records to DataFrame and predict
        df_day = pd.DataFrame(day_records)

        features = [
            "sell_price",
            "wday",
            "month",
            "year",
            "is_weekend",
            "is_holiday",
            "snap_CA",
            "snap_TX",
            "snap_WI",
            "lag_7",
            "lag_14",
            "lag_28",
            "rolling_7_avg",
            "rolling_30_avg",
        ]

        # Model Inference
        predicted_sales = model.predict(df_day[features])
        # Clip to positive integer
        df_day["sales"] = np.clip(predicted_sales, 0, None).round().astype(int)

        # Append predicted day back to df_recursive to feed into future lags
        df_recursive = pd.concat([df_recursive, df_day[cols_to_keep]], ignore_index=True)

    # Return only predicted rows (future dates)
    df_forecast = df_recursive[df_recursive["date"] > max_hist_date].copy()
    df_forecast["revenue"] = df_forecast["sales"] * df_forecast["sell_price"]

    logger.info("30-day recursive forecast generation complete.")
    return df_forecast


def save_forecast_results_to_gold(df_forecast: pd.DataFrame) -> None:
    """Saves forecast projections into Gold Delta tables for dashboard ingestion."""
    logger.info("Saving forecast outputs to Gold storage layer...")

    forecast_dir = settings.gold_dir / "gold_forecast_results"
    forecast_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as parquet part file inside directory to mimic Spark delta output
    parquet_file = forecast_dir / "part-0.parquet"
    df_forecast.to_parquet(str(parquet_file), index=False)
    logger.info(f"Forecast outcomes successfully stored in: {forecast_dir}")


def run_forecasting() -> dict:
    """Orchestrates model training, evaluation, and recursive forecasting."""
    # 1. Load history
    df_hist = load_gold_data_to_pandas()

    # 2. Train model
    model, metrics = train_forecasting_model(df_hist)

    # 3. Forecast future
    df_forecast = generate_30day_forecast(df_hist, model)

    # 4. Save results
    save_forecast_results_to_gold(df_forecast)

    # Save metrics in joblib for API consumption
    joblib.dump(metrics, settings.models_dir / "evaluation_metrics.joblib")

    return metrics


if __name__ == "__main__":
    run_forecasting()
