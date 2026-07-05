"""
PySpark ETL pipeline for Medallion Architecture (Bronze & Silver layers).
Includes raw data ingestion, schema validation, data cleaning, and melting (unpivoting).
"""
from __future__ import annotations

from pathlib import Path
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, expr, when

from src.config import settings
from src.db_connection import get_spark_session
from src.generate_mock_data import generate_mock_m5_data
from src.logger import logger


def check_and_prepare_raw_data() -> None:
    """Verifies that raw CSV files exist; generates mock data if missing."""
    calendar_file = settings.raw_dir / "calendar.csv"
    prices_file = settings.raw_dir / "sell_prices.csv"
    sales_file = settings.raw_dir / "sales_train_validation.csv"

    if not (calendar_file.exists() and prices_file.exists() and sales_file.exists()):
        logger.warning("Raw M5 dataset files missing from data/raw/. Generating synthetic mock data...")
        generate_mock_m5_data()
    else:
        logger.info("Raw M5 files located in data/raw/ directory.")


def run_bronze_layer(spark: SparkSession) -> tuple[DataFrame, DataFrame, DataFrame]:
    """Ingests raw CSV data and stores it in Bronze Delta tables."""
    logger.info("--- Starting Bronze Layer Ingestion ---")

    # Ingest Calendar CSV
    calendar_csv = str(settings.raw_dir / "calendar.csv")
    logger.info(f"Ingesting calendar CSV from: {calendar_csv}")
    bronze_calendar = spark.read.option("header", "true").option("inferSchema", "true").csv(calendar_csv)

    # Ingest Prices CSV
    prices_csv = str(settings.raw_dir / "sell_prices.csv")
    logger.info(f"Ingesting sell prices CSV from: {prices_csv}")
    bronze_prices = spark.read.option("header", "true").option("inferSchema", "true").csv(prices_csv)

    # Ingest Sales CSV
    sales_csv = str(settings.raw_dir / "sales_train_validation.csv")
    logger.info(f"Ingesting sales train validation CSV from: {sales_csv}")
    bronze_sales = spark.read.option("header", "true").option("inferSchema", "true").csv(sales_csv)

    # Write raw data to Bronze Delta Tables
    logger.info("Writing Bronze Delta tables...")
    bronze_calendar.write.format("delta").mode("overwrite").save(str(settings.bronze_dir / "bronze_calendar"))
    bronze_prices.write.format("delta").mode("overwrite").save(str(settings.bronze_dir / "bronze_prices"))

    # Apply sampling limit to sales if configured (speeds up local runs)
    if settings.sample_limit > 0:
        logger.info(f"Applying local sample limit: keeping first {settings.sample_limit} rows of sales data.")
        bronze_sales = bronze_sales.limit(settings.sample_limit)

    bronze_sales.write.format("delta").mode("overwrite").save(str(settings.bronze_dir / "bronze_sales"))
    logger.info("Bronze Layer successfully written.")

    return bronze_calendar, bronze_prices, bronze_sales


def run_silver_layer(
    spark: SparkSession,
    bronze_calendar: DataFrame,
    bronze_prices: DataFrame,
    bronze_sales: DataFrame,
) -> tuple[DataFrame, DataFrame, DataFrame]:
    """Cleans raw data and saves it to Silver Delta tables."""
    logger.info("--- Starting Silver Layer Processing ---")

    # 1. Clean Calendar
    logger.info("Cleaning calendar data...")
    silver_calendar = (
        bronze_calendar.withColumn("date", col("date").cast("date"))
        .withColumn("wm_yr_wk", col("wm_yr_wk").cast("integer"))
        .withColumn("wday", col("wday").cast("integer"))
        .withColumn("month", col("month").cast("integer"))
        .withColumn("year", col("year").cast("integer"))
        .withColumn("snap_CA", col("snap_CA").cast("integer"))
        .withColumn("snap_TX", col("snap_TX").cast("integer"))
        .withColumn("snap_WI", col("snap_WI").cast("integer"))
        .na.fill({"event_name_1": "", "event_type_1": "", "event_name_2": "", "event_type_2": ""})
    )

    # 2. Clean Sell Prices
    logger.info("Cleaning sell prices data...")
    silver_prices = (
        bronze_prices.withColumn("wm_yr_wk", col("wm_yr_wk").cast("integer"))
        .withColumn("sell_price", col("sell_price").cast("double"))
        .filter(col("sell_price") > 0.0)
    )

    # 3. Clean & Prepare Sales (deduplicate and filter out empty columns)
    logger.info("Cleaning sales data...")
    silver_sales = bronze_sales.dropDuplicates(["id"])

    # Write Silver tables
    logger.info("Writing Silver Delta tables...")
    silver_calendar.write.format("delta").mode("overwrite").save(str(settings.silver_dir / "silver_calendar"))
    silver_prices.write.format("delta").mode("overwrite").save(str(settings.silver_dir / "silver_prices"))
    silver_sales.write.format("delta").mode("overwrite").save(str(settings.silver_dir / "silver_sales"))
    logger.info("Silver Layer successfully written.")

    return silver_calendar, silver_prices, silver_sales


def melt_and_join_sales(
    spark: SparkSession,
    silver_sales: DataFrame,
    silver_calendar: DataFrame,
    silver_prices: DataFrame,
) -> DataFrame:
    """Melts horizontal day columns from sales DataFrame and joins with calendar & prices."""
    logger.info("Melting horizontal sales table to long format...")

    # Identify all day columns (e.g. d_1, d_2, ...)
    day_columns = [col_name for col_name in silver_sales.columns if col_name.startswith("d_")]

    # Melt (unpivot) horizontal columns using Spark's stack function
    # stack(N, 'col1', col1, 'col2', col2, ...) as (d, sales)
    stack_items = [f"'{c}', `{c}`" for c in day_columns]
    stack_expr = f"stack({len(day_columns)}, {', '.join(stack_items)}) as (d, sales)"

    melted_sales = silver_sales.select(
        col("id"),
        col("item_id"),
        col("dept_id"),
        col("cat_id"),
        col("store_id"),
        col("state_id"),
        expr(stack_expr),
    ).withColumn("sales", col("sales").cast("integer"))

    logger.info("Joining melted sales with calendar and sell prices...")

    # Join melted sales with calendar on 'd'
    sales_cal = melted_sales.join(silver_calendar, on="d", how="inner")

    # Join with sell prices on (store_id, item_id, wm_yr_wk)
    integrated_df = sales_cal.join(
        silver_prices,
        on=["store_id", "item_id", "wm_yr_wk"],
        how="inner",
    ).withColumn("revenue", col("sales") * col("sell_price"))

    return integrated_df


def run_etl() -> None:
    """Executes the entire Bronze & Silver ETL pipeline."""
    check_and_prepare_raw_data()
    spark = get_spark_session()
    try:
        b_cal, b_pr, b_sal = run_bronze_layer(spark)
        s_cal, s_pr, s_sal = run_silver_layer(spark, b_cal, b_pr, b_sal)
        integrated = melt_and_join_sales(spark, s_sal, s_cal, s_pr)

        integrated_path = str(settings.silver_dir / "silver_integrated")
        logger.info(f"Saving integrated dataset to: {integrated_path}")
        integrated.write.format("delta").mode("overwrite").save(integrated_path)
        logger.info("ETL pipeline successfully processed Bronze & Silver.")
    finally:
        # Keep Spark session open if running in backend, or close here.
        # It's cleaner to stop it to release memory.
        spark.stop()
        logger.info("Spark session closed.")


if __name__ == "__main__":
    run_etl()
