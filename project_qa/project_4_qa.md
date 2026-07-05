# Project Q&A: RetailSense AI (Project 4)

This document answers the most frequent questions about the architecture, codebase, and algorithms used in the **RetailSense AI** project.

---

## ❓ General Platform Questions

### Q1: What is the main objective of RetailSense AI?
**A**: RetailSense AI is an end-to-end retail intelligence platform that ingests raw transaction, pricing, and calendar data (modeled after the M5 Walmart forecasting dataset), processes it through a PySpark Medallion pipeline (Bronze -> Silver -> Gold), trains an XGBoost model to forecast unit sales for the next 30 days, and exposes business analytics via an interactive Streamlit dashboard and a Grok LLM-powered natural language assistant.

### Q2: What tech stack is used in the project?
**A**:
*   **Data Processing**: PySpark (Apache Spark 3.5.1)
*   **Storage Layer**: Delta Lake (delta-spark 3.1.0)
*   **Machine Learning**: XGBoost, Scikit-Learn
*   **Backend API**: FastAPI, Uvicorn
*   **Frontend Dashboard**: Streamlit, Matplotlib, Seaborn
*   **LLM Integration**: Groq/Grok API (via OpenAI SDK wrapper)

---

## 📂 Data Pipeline Questions

### Q3: Why did we unpivot/melt the daily sales data?
**A**: In the raw M5 dataset, sales are formatted horizontally where each day is a column (e.g. `d_1`, `d_2`, ..., `d_1913`). This wide format is extremely inefficient for SQL filtering, joining, and model training. 
By unpivoting (melting) the day columns into a **vertical row format** (with `date` and `sales` columns), we standardize the structure. This enables clean joins with calendar and pricing tables and allows database engine index partitioning on date fields.

### Q4: How do the Bronze, Silver, and Gold tables relate?
**A**:
1. **Bronze**: Stores raw unpivoted DataFrames exactly as ingested.
2. **Silver**: Cleans null values, enforces correct data types (e.g., converting prices to float), and joins sales with prices and calendar attributes.
3. **Gold**: Groups Silver data to build summarized business tables:
   - `gold_daily_sales`: Aggregate revenue and unit sales per day.
   - `gold_store_performance`: Total revenue, units sold, and average price per store.
   - `gold_product_performance`: Total revenue, units sold, and average price per product.
   - `gold_state_sales`: Regional sales KPIs.
   - `gold_forecasting_input`: Cleaned history containing rolling averages and lags, used to train the model.
   - `gold_forecast_results`: The 30-day forecast outputs.

---

## 🤖 Machine Learning Questions

### Q5: What features are engineered for the forecasting model?
**A**:
*   **Time-series Lags**: `lag_7` (sales 7 days ago), `lag_14`, `lag_28`.
*   **Rolling Statistics**: `rolling_7_avg` and `rolling_30_avg` (smoothed trend).
*   **Calendar Features**: `wday` (day of week), `month`, `year`, `is_weekend`, `is_holiday` (snap indicators for states).
*   **Pricing**: Current `sell_price` of the item.

### Q6: How does the recursive forecasting work?
**A**: 
Because time-series models predict the future based on past lags, we cannot predict $t+2$ directly because the actual sales value for $t+1$ is unknown.
To solve this:
1. The model predicts sales for Day 1 ($t+1$).
2. The predicted value is appended to the historical dataset.
3. The lag features are re-calculated using this prediction.
4. The model predicts Day 2 ($t+2$) using the calculated lags.
5. This loop repeats recursively for 30 steps to construct the full 30-day forecast.

---

## 🔌 API & LLM Questions

### Q7: How does the AI Assistant answer user queries?
**A**:
1. The user asks a question in the chat box (e.g. "Suggest inventory actions for the Foods category").
2. The FastAPI backend endpoint (`/api/chat`) runs SQL queries against the Gold Delta/Parquet tables to calculate current metrics (total sales, top products, worst performing items).
3. The API structures these metrics into a short context prompt.
4. The API queries the Grok/Groq LLM model with the prompt:
   ```text
   You are an expert retail analyst. Here is the current performance summary: [summary].
   User Question: [question]
   Answer the question clearly based on the provided numbers.
   ```
5. The LLM processes the question using the precise KPIs, returning an accurate, context-aware analysis without hallucinating numbers.
