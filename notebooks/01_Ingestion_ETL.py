# Databricks notebook source
# MAGIC %md
# MAGIC # Phase 1: Ingestion & Medallion ETL (Bronze & Silver Layers)
# MAGIC 
# MAGIC This notebook runs the raw files ingestion, basic cleaning, schema verification, and unpivots the daily sales columns to write the Bronze and Silver Delta tables.
# MAGIC 
# MAGIC ### Instructions
# MAGIC 1. Ensure you have cloned this repository into a Databricks Git Folder (Workspace -> Repos).
# MAGIC 2. Set the `RAW_DIR`, `BRONZE_DIR`, and `SILVER_DIR` environment variables if you want to write to DBFS or ADLS instead of the Git Workspace local storage.
# MAGIC 3. Set `SAMPLE_LIMIT = 0` in environment variables if you want to run on the entire M5 dataset (not just the local test limit).

# COMMAND ----------
# MAGIC %md
# MAGIC ### 1. Setup Environment Path & Imports

# COMMAND ----------
import sys
import os

# Get path of the current notebook and resolve repo root to allow module imports
repo_root = os.path.abspath("..")
if repo_root not in sys.path:
    sys.path.append(repo_root)

# COMMAND ----------
from src.config import settings
from src.etl_pipeline import run_etl
from src.logger import logger

# COMMAND ----------
# MAGIC %md
# MAGIC ### 2. Print Current Ingestion Configurations

# COMMAND ----------
logger.info(f"PROJECT ROOT resolved: {repo_root}")
logger.info(f"Ingesting raw data from: {settings.raw_dir}")
logger.info(f"Writing Bronze Delta tables to: {settings.bronze_dir}")
logger.info(f"Writing Silver Delta tables to: {settings.silver_dir}")
logger.info(f"Sample processing limit configured: {settings.sample_limit} (0 means full dataset)")

# COMMAND ----------
# MAGIC %md
# MAGIC ### 3. Execute PySpark ETL Pipeline

# COMMAND ----------
run_etl()

# COMMAND ----------
# MAGIC %md
# MAGIC ### 4. Verify Tables in DBFS / Storage

# COMMAND ----------
# Display the list of files created in the Silver directory
dbutils.fs.ls(str(settings.silver_dir).replace("/Workspace", ""))
