# Databricks notebook source
# MAGIC %md
# MAGIC # RetailSense AI - Executive Insights Dashboard
# MAGIC 
# MAGIC This notebook serves as an interactive business dashboard. It reads the Gold analytical tables and visualizes key sales trends, product rankings, and future forecasts.
# MAGIC 
# MAGIC ### How to Publish as a Databricks Dashboard:
# MAGIC 1. Run this notebook on your compute cluster to populate all charts.
# MAGIC 2. In the top right corner of the notebook menu, click **View** -> **Dashboards** -> **New Dashboard** (or click **Publish** for Lakeview Dashboards).
# MAGIC 3. Drag and drop the visualization cells to organize them into a clean business layout.

# COMMAND ----------
# MAGIC %md
# MAGIC ### 1. Setup Filters (Widgets)
# MAGIC Configure interactive dropdowns to allow business users to filter metrics dynamically.

# COMMAND ----------
# Create interactive widgets
dbutils.widgets.text("State", "All", "Filter by State")
dbutils.widgets.text("Category", "All", "Filter by Category")

# COMMAND ----------
state_filter = dbutils.widgets.get("State")
category_filter = dbutils.widgets.get("Category")

# COMMAND ----------
# MAGIC %md
# MAGIC ### 2. Executive KPI Cards
# MAGIC Let's query and calculate overall revenue, sales volume, and number of products.

# COMMAND ----------
from pyspark.sql.functions import sum, count, col, lit
from src.config import settings

# Load Gold tables
df_daily = spark.read.format("delta").load(str(settings.gold_dir / "gold_daily_sales"))
df_stores = spark.read.format("delta").load(str(settings.gold_dir / "gold_store_performance"))
df_products = spark.read.format("delta").load(str(settings.gold_dir / "gold_product_performance"))

# Apply widget filters
if state_filter != "All":
    df_daily = df_daily.filter(col("state_id") == state_filter)
    
if category_filter != "All":
    df_daily = df_daily.filter(col("cat_id") == category_filter)

# Calculate KPIs
kpi = df_daily.select(
    sum("revenue").alias("Total_Revenue"),
    sum("sales").alias("Total_Units_Sold"),
    count("id").alias("Record_Count")
)
display(kpi)

# COMMAND ----------
# MAGIC %md
# MAGIC ### 3. Daily Revenue Trends
# MAGIC Visualizes sales fluctuations over time. Select the **Line Chart** visualization in Databricks.

# COMMAND ----------
df_trend = df_daily.groupBy("date").agg(sum("revenue").alias("Daily_Revenue")).orderBy("date")
display(df_trend)

# COMMAND ----------
# MAGIC %md
# MAGIC ### 4. Store Rankings by Performance
# MAGIC Displays revenue contribution by individual retail stores. Select **Bar Chart** visualization.

# COMMAND ----------
display(df_stores.orderBy(col("total_revenue").desc()))

# COMMAND ----------
# MAGIC %md
# MAGIC ### 5. Top 10 Best Selling Products
# MAGIC Visualizes highest revenue generating item identifiers. Select **Bar Chart** or **Table** visualization.

# COMMAND ----------
top_products = df_products.orderBy(col("total_revenue").desc()).limit(10)
display(top_products)

# COMMAND ----------
# MAGIC %md
# MAGIC ### 6. Historical Sales vs. 30-Day XGBoost Forecast
# MAGIC Combines actual historical sales with predicted projections to show future trends. Select **Line Chart** or **Area Chart** with `date` as X-axis and `sales` as Y-axis, grouped by `type` (Actual vs. Forecast).

# COMMAND ----------
# Load forecasting outputs
df_forecast = spark.read.format("delta").load(str(settings.gold_dir / "gold_forecast_results"))

# Prepare actual daily sales
df_actual_daily = df_daily.groupBy("date").agg(sum("sales").alias("sales")).withColumn("type", lit("Actual"))

# Prepare forecasted daily sales
df_forecast_daily = df_forecast.groupBy("date").agg(sum("sales").alias("sales")).withColumn("type", lit("Forecast"))

# Union actual and forecast sales
df_comparison = df_actual_daily.union(df_forecast_daily).orderBy("date")
display(df_comparison)
