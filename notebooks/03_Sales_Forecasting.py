# Databricks notebook source
# MAGIC %md
# MAGIC # Phase 3: Sales Forecasting & Model Training (XGBoost)
# MAGIC 
# MAGIC This notebook trains an XGBoost Regressor model on Gold layer features, evaluates forecast accuracy metrics, saves the model artifact, and performs recursive 30-day unit projections.
# MAGIC 
# MAGIC ### Cluster Requirement
# MAGIC Ensure your Databricks cluster has `xgboost` and `scikit-learn` installed. You can install these via Databricks Library manager or run:
# MAGIC `%pip install xgboost scikit-learn` in a command cell.

# COMMAND ----------
# MAGIC %pip install xgboost scikit-learn

# COMMAND ----------
# MAGIC %md
# MAGIC ### 1. Setup Environment Path & Imports

# COMMAND ----------
import sys
import os

# Resolve repo root path to allow imports
repo_root = os.path.abspath("..")
if repo_root not in sys.path:
    sys.path.append(repo_root)

# COMMAND ----------
from src.config import settings
from src.forecasting import run_forecasting
from src.logger import logger

# COMMAND ----------
# MAGIC %md
# MAGIC ### 2. Print Current Forecasting Settings

# COMMAND ----------
logger.info(f"PROJECT ROOT resolved: {repo_root}")
logger.info(f"Loading Gold forecasting data from: {settings.gold_dir / 'gold_forecasting_input'}")
logger.info(f"Saving trained model to: {settings.models_dir / 'xgboost_forecaster.joblib'}")
logger.info(f"Writing forecast results to: {settings.gold_dir / 'gold_forecast_results'}")

# COMMAND ----------
# MAGIC %md
# MAGIC ### 3. Execute Model Training & Projection

# COMMAND ----------
metrics = run_forecasting()

# COMMAND ----------
# MAGIC %md
# MAGIC ### 4. Print Training Metrics Summary

# COMMAND ----------
import json
print("=================== TRAINING RESULTS ===================")
print(json.dumps(metrics, indent=4))
print("========================================================")
