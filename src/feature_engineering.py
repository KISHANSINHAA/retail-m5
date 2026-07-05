"""
PySpark feature engineering and Gold layer creation.
Calculates time, sales, lags, rolling statistics, and business aggregates.
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import avg, col, count, dayofweek, lag, month, sum, when
from pyspark.sql.window import Window

from src.config import settings
from src.db_connection import get_spark_session
from src.logger import logger


def compute_time_features(df: DataFrame) -> DataFrame:
    """Extracts date/time features from the integrated DataFrame."""
    logger.info("Computing calendar time features...")
    return (
        df.withColumn("year", col("year").cast("integer"))
        .withColumn("month", col("month").cast("integer"))
        .withColumn("week", col("wday").cast("integer"))  # wday is 1-7 in M5
        # Weekend flag (in M5 wday=1 is Sat, wday=2 is Sun)
        .withColumn("is_weekend", when(col("wday").isin(1, 2), 1).otherwise(0))
        # Holiday flag (event_name_1 is non-empty)
        .withColumn("is_holiday", when(col("event_name_1") != "", 1).otherwise(0))
    )


def compute_lag_and_rolling_features(df: DataFrame) -> DataFrame:
    """Computes lags and rolling statistics over product-store partition."""
    logger.info("Computing sales lags and rolling averages (using Window functions)...")

    # Define partition window by unique product-store combination (id) ordered by date
    window_spec = Window.partitionBy("id").orderBy("date")

    # Lag features
    df = df.withColumn("lag_7", lag("sales", 7).over(window_spec))
    df = df.withColumn("lag_14", lag("sales", 14).over(window_spec))
    df = df.withColumn("lag_28", lag("sales", 28).over(window_spec))

    # Rolling average features (excluding current day to prevent data leakage)
    window_7d = Window.partitionBy("id").orderBy("date").rowsBetween(-7, -1)
    df = df.withColumn("rolling_7_avg", avg("sales").over(window_7d))

    window_30d = Window.partitionBy("id").orderBy("date").rowsBetween(-30, -1)
    df = df.withColumn("rolling_30_avg", avg("sales").over(window_30d))

    # Drop null rows created by lags/rolling averages to keep dataset clean
    df = df.na.drop(subset=["lag_7", "lag_14", "lag_28", "rolling_7_avg", "rolling_30_avg"])

    return df


def build_gold_layer_tables(spark: SparkSession, df: DataFrame) -> None:
    """Aggregates and stores Gold business tables."""
    logger.info("--- Starting Gold Layer Aggregations ---")

    # 1. gold_daily_sales: Total daily revenue and units sold
    logger.info("Creating gold_daily_sales...")
    gold_daily_sales = df.groupBy("date", "year", "month", "wday", "is_holiday").agg(
        sum("sales").alias("total_units"),
        sum("revenue").alias("total_revenue"),
    )
    gold_daily_sales.write.format("delta").mode("overwrite").save(str(settings.gold_dir / "gold_daily_sales"))

    # 2. gold_store_performance: Store sales, revenue, and average price
    logger.info("Creating gold_store_performance...")
    gold_store_performance = df.groupBy("store_id", "state_id").agg(
        sum("sales").alias("total_units"),
        sum("revenue").alias("total_revenue"),
        avg("sell_price").alias("avg_sell_price"),
    )
    gold_store_performance.write.format("delta").mode("overwrite").save(str(settings.gold_dir / "gold_store_performance"))

    # 3. gold_product_performance: Product revenue, unit sales, category
    logger.info("Creating gold_product_performance...")
    gold_product_performance = df.groupBy("item_id", "dept_id", "cat_id").agg(
        sum("sales").alias("total_units"),
        sum("revenue").alias("total_revenue"),
    )
    gold_product_performance.write.format("delta").mode("overwrite").save(str(settings.gold_dir / "gold_product_performance"))

    # 4. gold_category_sales: Category metrics
    logger.info("Creating gold_category_sales...")
    gold_category_sales = df.groupBy("cat_id").agg(
        sum("sales").alias("total_units"),
        sum("revenue").alias("total_revenue"),
    )
    gold_category_sales.write.format("delta").mode("overwrite").save(str(settings.gold_dir / "gold_category_sales"))

    # 5. gold_state_sales: State revenue performance
    logger.info("Creating gold_state_sales...")
    gold_state_sales = df.groupBy("state_id").agg(
        sum("sales").alias("total_units"),
        sum("revenue").alias("total_revenue"),
    )
    gold_state_sales.write.format("delta").mode("overwrite").save(str(settings.gold_dir / "gold_state_sales"))

    # 6. gold_monthly_sales: Monthly historical sales
    logger.info("Creating gold_monthly_sales...")
    gold_monthly_sales = df.groupBy("year", "month").agg(
        sum("sales").alias("total_units"),
        sum("revenue").alias("total_revenue"),
    )
    gold_monthly_sales.write.format("delta").mode("overwrite").save(str(settings.gold_dir / "gold_monthly_sales"))

    # 7. gold_forecasting_input: Final ML training dataset
    logger.info("Creating gold_forecasting_input...")
    df.write.format("delta").mode("overwrite").save(str(settings.gold_dir / "gold_forecasting_input"))

    logger.info("Gold Layer tables successfully generated.")


def run_feature_engineering() -> None:
    """Runs the feature engineering process to create Gold tables."""
    spark = get_spark_session()
    try:
        integrated_path = str(settings.silver_dir / "silver_integrated")
        logger.info(f"Loading integrated Silver table from: {integrated_path}")
        integrated_df = spark.read.format("delta").load(integrated_path)

        # 1. Compute time features
        time_df = compute_time_features(integrated_df)

        # 2. Compute lag & rolling stats
        features_df = compute_lag_and_rolling_features(time_df)

        # 3. Create Gold Tables
        build_gold_layer_tables(spark, features_df)

        logger.info("Feature engineering and Gold layer creation complete.")
    finally:
        spark.stop()
        logger.info("Spark session closed.")


if __name__ == "__main__":
    run_feature_engineering()
