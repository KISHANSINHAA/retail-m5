# RetailSense AI: Retail Analytics & Sales Forecasting Platform

RetailSense AI is an end-to-end retail intelligence platform that processes retail transactions, implements a Medallion Architecture (Bronze, Silver, Gold) using PySpark and Delta Lake, trains an XGBoost ML forecasting model, and exposes interactive analytics and an AI Retail Assistant via FastAPI and Streamlit.

---

## 🏗️ Medallion Architecture Flow

1.  **Raw Ingestion:** Ingests `calendar.csv`, `sales_train_validation.csv`, and `sell_prices.csv` from `data/raw/`.
2.  **Bronze Layer:** Preserves the raw data exactly as-received in Delta format under `data/bronze/`.
3.  **Silver Layer:** Cleans datasets (data type casts, date standardization, null/negative handling, deduplication) under `data/silver/`.
    *   **Data Integration (Melting):** Melts the horizontal daily sales columns (`d_1` to `d_N`) to a long table and joins with calendar and sell prices to calculate revenue (`sales * sell_price`).
4.  **Gold Layer:** Generates high-performance analytical aggregates and ML features under `data/gold/`:
    *   `gold_daily_sales`: Daily units and revenue aggregates.
    *   `gold_store_performance`: Store-level cumulative revenue and pricing metrics.
    *   `gold_product_performance`: Product and category sales trends.
    *   `gold_forecasting_input`: Enriched dataset containing lag features (`lag_7`, `lag_14`, `lag_28`) and rolling statistics (`rolling_7_avg`, `rolling_30_avg`) ready for model training.

---

## 🔮 Sales Forecasting Model

*   Trains a high-performance **XGBoost Regressor** on Gold feature tables.
*   Implements **recursive forecasting** to predict unit sales for the next 30 days.
*   Saves outputs to `data/gold/gold_forecast_results` for immediate visual querying.

---

## 💬 AI Retail Assistant (Grok/Groq LLM Integration)

*   FastAPI backend retrieves a structured KPI summary from Gold Delta Tables.
*   Avoids sending raw millions of rows to keep LLM token costs minimal and response latencies low.
*   Sends the structured summary along with the user's natural language question to the Grok/Groq API.

---

## 🚀 Quick Start (Local Setup)

### 1. Set Up Virtual Environment & Dependencies

Make sure you have Java 8/11/17/21 installed for PySpark execution.

```bash
cd project/4
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

1.  Rename `.env.example` to `.env`.
2.  Provide your Groq or Grok API Key:
    ```env
    LLM_API_KEY=your-api-key-here
    LLM_API_URL=https://api.groq.com/openai/v1
    LLM_MODEL_NAME=llama-3.3-70b-versatile
    ```

### 3. Run Ingestion, ETL, and Model Training

To trigger the complete PySpark ingestion and model forecasting pipeline locally:
```bash
.venv\Scripts\python -m src.etl_pipeline
.venv\Scripts\python -m src.feature_engineering
.venv\Scripts\python -m src.forecasting
```
*(Alternatively, you can trigger this programmatically via the API `/api/etl/run`)*

### 4. Launch Backend API

Start the FastAPI REST backend:
```bash
.venv\Scripts\uvicorn api.main:app --reload --port 8000
```
Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to view the Swagger API documentation.

### 5. Launch Streamlit Dashboard

Start the front-end interactive UI:
```bash
.venv\Scripts\streamlit run app/streamlit_app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🧪 Running Automated Tests

Run the test suite using `pytest`:
```bash
.venv\Scripts\pytest tests/
```
