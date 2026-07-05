# Databricks notebook source
# MAGIC %md
# MAGIC # Phase 2: Feature Engineering & Gold Layer Calculations
# MAGIC 
# MAGIC This notebook aggregates Silver data and calculates rolling averages, lags, calendar attributes, and store/product performance metrics to build Gold Delta tables.

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
from src.feature_engineering import run_feature_engineering
from src.logger import logger

# COMMAND ----------
# MAGIC %md
# MAGIC ### 2. Print Current Gold Configurations

# COMMAND ----------
logger.info(f"PROJECT ROOT resolved: {repo_root}")
logger.info(f"Reading Silver data from: {settings.silver_dir}")
logger.info(f"Writing Gold Delta tables to: {settings.gold_dir}")

# COMMAND ----------
# MAGIC %md
# MAGIC ### 3. Run PySpark Feature Engineering Pipeline

# COMMAND ----------
run_feature_engineering()

# COMMAND ----------
# MAGIC %md
# MAGIC ### 4. Check Gold Tables Created

# COMMAND ----------
# Display the list of files/tables created in the Gold directory
dbutils.fs.ls(str(settings.gold_dir).replace("/Workspace", ""))
