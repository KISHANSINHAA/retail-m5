"""
FastAPI Backend Server for RetailSense AI.
Provides routes for running ETL, fetching KPIs, retrieving forecast plots, and AI Chat Assistant.
"""
from __future__ import annotations

import os
import time
import joblib
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.logger import logger
from src.llm_client import generate_llm_response
from api.schemas import (
    ChatRequest,
    ChatResponse,
    ETLStatusResponse,
    KPIsResponse,
    ForecastPoint,
    ForecastResponse,
    StorePerformance,
    ProductPerformance,
    CategoryPerformance,
    StatePerformance,
)

app = FastAPI(
    title="RetailSense AI API",
    description="Analytics and forecasting backend for the M5 retail platform.",
    version="1.0.0",
)

# Enable CORS for Streamlit frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track running background ETL tasks
ETL_RUNNING_STATUS = {"status": "idle", "error": None}


def run_full_etl_job():
    """Background task function to run the full Spark ETL and Forecast pipeline."""
    global ETL_RUNNING_STATUS
    ETL_RUNNING_STATUS["status"] = "running"
    ETL_RUNNING_STATUS["error"] = None
    logger.info("Background ETL and Forecasting job triggered.")

    try:
        # Import pipeline functions locally to ensure correct activation
        from src.etl_pipeline import run_etl
        from src.feature_engineering import run_feature_engineering
        from src.forecasting import run_forecasting

        logger.info("Step 1: Running Ingestion and Silver Medallion ETL...")
        run_etl()

        logger.info("Step 2: Running Gold Feature Engineering...")
        run_feature_engineering()

        logger.info("Step 3: Training XGBoost and generating recursive 30-day forecast...")
        metrics = run_forecasting()

        ETL_RUNNING_STATUS["status"] = "completed"
        logger.info(f"Background ETL Job completed successfully. Metrics: {metrics}")
    except Exception as e:
        logger.exception("Error occurred in background ETL pipeline job.")
        ETL_RUNNING_STATUS["status"] = "failed"
        ETL_RUNNING_STATUS["error"] = str(e)


def _check_tables_exist() -> Dict[str, bool]:
    """Helper to verify which Gold tables are populated on disk."""
    tables = [
        "gold_daily_sales",
        "gold_store_performance",
        "gold_product_performance",
        "gold_category_sales",
        "gold_state_sales",
        "gold_forecast_results",
    ]
    status = {}
    for table in tables:
        path = settings.gold_dir / table
        # Check if folder exists and has at least one parquet file
        if path.exists() and path.is_dir():
            parquet_files = list(path.glob("*.parquet"))
            status[table] = len(parquet_files) > 0
        else:
            status[table] = False
    return status


@app.get("/api/etl/status", response_model=ETLStatusResponse)
async def get_etl_status():
    """Gets the status of the Medallion Delta Lake and forecasting models."""
    tables = _check_tables_exist()
    model_path = settings.models_dir / "xgboost_forecaster.joblib"
    model_exists = model_path.exists()

    metrics_path = settings.models_dir / "evaluation_metrics.joblib"
    metrics = None
    if metrics_path.exists():
        try:
            metrics = joblib.load(metrics_path)
        except Exception:
            pass

    current_status = "pending_etl"
    if ETL_RUNNING_STATUS["status"] == "running":
        current_status = "running"
    elif ETL_RUNNING_STATUS["status"] == "failed":
        current_status = f"failed: {ETL_RUNNING_STATUS['error']}"
    elif all(tables.values()) and model_exists:
        current_status = "ready"

    return ETLStatusResponse(
        status=current_status,
        tables_exist=tables,
        model_exists=model_exists,
        metrics=metrics,
    )


@app.post("/api/etl/run")
async def run_etl_pipeline(background_tasks: BackgroundTasks):
    """Triggers the full ingestion, feature engineering, and model training asynchronously."""
    global ETL_RUNNING_STATUS
    if ETL_RUNNING_STATUS["status"] == "running":
        return {"status": "already_running", "message": "ETL job is already running in background."}

    background_tasks.add_task(run_full_etl_job)
    return {"status": "started", "message": "ETL and forecasting pipeline launched in background."}


@app.get("/api/analytics/kpis", response_model=KPIsResponse)
async def get_kpi_dashboard_metrics():
    """Retrieves aggregated KPIs from Gold Delta Tables for the main dashboard views."""
    tables = _check_tables_exist()
    if not all(tables.values()):
        raise HTTPException(
            status_code=400,
            detail="ETL tables are missing or not fully populated. Please trigger /api/etl/run first.",
        )

    try:
        # Load tables using standard pandas read_parquet (fast, direct, lightweight)
        df_daily = pd.read_parquet(str(settings.gold_dir / "gold_daily_sales"))
        df_store = pd.read_parquet(str(settings.gold_dir / "gold_store_performance"))
        df_prod = pd.read_parquet(str(settings.gold_dir / "gold_product_performance"))
        df_cat = pd.read_parquet(str(settings.gold_dir / "gold_category_sales"))
        df_state = pd.read_parquet(str(settings.gold_dir / "gold_state_sales"))

        # Calculate high level KPIs
        total_rev = float(df_daily["total_revenue"].sum())
        total_units = int(df_daily["total_units"].sum())
        avg_price = total_rev / total_units if total_units > 0 else 0.0

        # Calculate WoW Growth Rate
        df_daily["date"] = pd.to_datetime(df_daily["date"])
        df_daily = df_daily.sort_values("date")
        max_date = df_daily["date"].max()

        last_7_rev = float(df_daily[df_daily["date"] > max_date - pd.Timedelta(days=7)]["total_revenue"].sum())
        prev_7_rev = float(
            df_daily[
                (df_daily["date"] <= max_date - pd.Timedelta(days=7))
                & (df_daily["date"] > max_date - pd.Timedelta(days=14))
            ]["total_revenue"].sum()
        )
        growth_rate = ((last_7_rev - prev_7_rev) / prev_7_rev * 100) if prev_7_rev > 0 else 0.0

        # Format lists
        stores_list = [
            StorePerformance(
                store_id=r["store_id"],
                state_id=r["state_id"],
                total_units=int(r["total_units"]),
                total_revenue=float(r["total_revenue"]),
                avg_sell_price=float(r["avg_sell_price"]),
            )
            for _, r in df_store.iterrows()
        ]

        cats_list = [
            CategoryPerformance(
                cat_id=r["cat_id"],
                total_units=int(r["total_units"]),
                total_revenue=float(r["total_revenue"]),
            )
            for _, r in df_cat.iterrows()
        ]

        states_list = [
            StatePerformance(
                state_id=r["state_id"],
                total_units=int(r["total_units"]),
                total_revenue=float(r["total_revenue"]),
            )
            for _, r in df_state.iterrows()
        ]

        # Top & worst products (by revenue)
        df_prod_sorted = df_prod.sort_values("total_revenue", ascending=False)
        top_prods = [
            ProductPerformance(
                item_id=r["item_id"],
                dept_id=r["dept_id"],
                cat_id=r["cat_id"],
                total_units=int(r["total_units"]),
                total_revenue=float(r["total_revenue"]),
            )
            for _, r in df_prod_sorted.head(5).iterrows()
        ]

        worst_prods = [
            ProductPerformance(
                item_id=r["item_id"],
                dept_id=r["dept_id"],
                cat_id=r["cat_id"],
                total_units=int(r["total_units"]),
                total_revenue=float(r["total_revenue"]),
            )
            for _, r in df_prod_sorted.tail(5).iterrows()
        ]

        return KPIsResponse(
            total_revenue=total_rev,
            total_units_sold=total_units,
            average_selling_price=avg_price,
            growth_rate_wow=growth_rate,
            active_products=df_prod["item_id"].nunique(),
            active_stores=df_store["store_id"].nunique(),
            stores=stores_list,
            categories=cats_list,
            states=states_list,
            top_products=top_prods,
            worst_products=worst_prods,
        )
    except Exception as e:
        logger.exception("Failed to compile dashboard KPIs.")
        raise HTTPException(status_code=500, detail=f"Failed to generate analytics metrics: {e}")


@app.get("/api/forecast/predict", response_model=ForecastResponse)
async def get_sales_forecast():
    """Returns historical daily trends combined with recursive 30-day forecasted results."""
    tables = _check_tables_exist()
    if not tables.get("gold_daily_sales") or not tables.get("gold_forecast_results"):
        raise HTTPException(
            status_code=400,
            detail="ETL/Forecast tables missing. Run ETL and forecasting model first.",
        )

    try:
        # Load historical daily sales
        df_hist = pd.read_parquet(str(settings.gold_dir / "gold_daily_sales"))
        df_hist["date"] = pd.to_datetime(df_hist["date"])
        df_hist = df_hist.sort_values("date")

        # Load forecasts
        df_fore = pd.read_parquet(str(settings.gold_dir / "gold_forecast_results"))
        df_fore["date"] = pd.to_datetime(df_fore["date"])

        # Aggregate forecast to daily level
        df_fore_daily = df_fore.groupby("date").agg(
            {"sales": "sum", "revenue": "sum"}
        ).reset_index().rename(columns={"sales": "total_units", "revenue": "total_revenue"})
        df_fore_daily = df_fore_daily.sort_values("date")

        # Compile points
        points = []

        # Keep last 90 days of history for clean chart representation
        cutoff_date = df_hist["date"].max() - pd.Timedelta(days=90)
        df_hist_filtered = df_hist[df_hist["date"] >= cutoff_date]

        for _, r in df_hist_filtered.iterrows():
            points.append(
                ForecastPoint(
                    date=r["date"].strftime("%Y-%m-%d"),
                    type="Historical",
                    sales=float(r["total_units"]),
                    revenue=float(r["total_revenue"]),
                )
            )

        for _, r in df_fore_daily.iterrows():
            points.append(
                ForecastPoint(
                    date=r["date"].strftime("%Y-%m-%d"),
                    type="Forecasted",
                    sales=float(r["total_units"]),
                    revenue=float(r["total_revenue"]),
                )
            )

        # Load model accuracy metrics
        metrics = None
        metrics_path = settings.models_dir / "evaluation_metrics.joblib"
        if metrics_path.exists():
            metrics = joblib.load(metrics_path)

        return ForecastResponse(points=points, metrics=metrics)
    except Exception as e:
        logger.exception("Failed to retrieve forecast projections.")
        raise HTTPException(status_code=500, detail=f"Inference failure: {e}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_assistant(req: ChatRequest):
    """Answers retail operational questions using Grok/Groq LLM guided by a Gold KPI summary context."""
    tables = _check_tables_exist()
    start_time = time.time()

    if not all(tables.values()):
        raise HTTPException(
            status_code=400,
            detail="ETL tables missing. Please run the ETL pipeline before asking questions.",
        )

    try:
        # 1. Compile KPIs to populate context
        df_daily = pd.read_parquet(str(settings.gold_dir / "gold_daily_sales"))
        df_store = pd.read_parquet(str(settings.gold_dir / "gold_store_performance"))
        df_prod = pd.read_parquet(str(settings.gold_dir / "gold_product_performance"))
        df_cat = pd.read_parquet(str(settings.gold_dir / "gold_category_sales"))
        df_state = pd.read_parquet(str(settings.gold_dir / "gold_state_sales"))
        df_fore = pd.read_parquet(str(settings.gold_dir / "gold_forecast_results"))

        # Calculate high level statistics
        total_rev = df_daily["total_revenue"].sum()
        total_units = df_daily["total_units"].sum()

        top_store = df_store.sort_values("total_revenue", ascending=False).iloc[0]["store_id"]
        top_state = df_state.sort_values("total_revenue", ascending=False).iloc[0]["state_id"]
        top_cat = df_cat.sort_values("total_revenue", ascending=False).iloc[0]["cat_id"]

        # Calculate forecast numbers
        forecast_rev = df_fore["revenue"].sum()
        forecast_units = df_fore["sales"].sum()

        # Build KPI summary
        kpi_summary = (
            f"HISTORICAL GENERAL METRICS:\n"
            f"- Total Revenue: ${total_rev:,.2f}\n"
            f"- Total Units Sold: {total_units:,}\n"
            f"- Top Category: {top_cat}\n"
            f"- Top Performing Store: {top_store} (located in state {top_state})\n"
            f"- Top Performing State: {top_state}\n\n"
            f"FUTURE 30-DAY FORECAST METRICS:\n"
            f"- Forecasted Total Revenue: ${forecast_rev:,.2f}\n"
            f"- Forecasted Units Sold: {forecast_units:,}\n"
            f"- Average Forecasted Daily Sales: {forecast_units / 30:.1f} units\n"
        )

        # Build prompt
        system_message = (
            "You are RetailSense AI Assistant, a senior retail business intelligence analyst. "
            "Your goal is to answer the user's question using the provided metrics summary context. "
            "Support your reasoning with numbers and provide clear, professional, actionable business recommendations. "
            "Adhere to the following guidelines:\n"
            "- Be concise and keep your response under 150-200 words.\n"
            "- Do not hallucinate or make up metrics not presented in the context.\n"
            "- Format output using clean Markdown (e.g. lists, bullet points, bold terms)."
        )

        prompt = (
            f"Here is the Gold Layer Business KPI and Forecasting Summary for our stores:\n"
            f"===================================================\n"
            f"{kpi_summary}\n"
            f"===================================================\n\n"
            f"User Question: {req.message}\n"
            f"Assistant Response:"
        )

        # Call LLM client
        response_text = generate_llm_response(prompt, system_message)
        latency = (time.time() - start_time) * 1000

        return ChatResponse(
            response=response_text,
            session_id=req.session_id,
            latency_ms=latency,
        )
    except Exception as e:
        logger.exception("AI assistant communication failure.")
        raise HTTPException(status_code=500, detail=f"LLM API or pipeline context error: {e}")
