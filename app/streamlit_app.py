"""
Streamlit Frontend Dashboard for RetailSense AI.
Provides rich visualizations, ETL status control, forecasting charts, and a retail LLM chatbot.
"""
from __future__ import annotations

import time
import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

# Set page config
st.set_page_config(
    page_title="RetailSense AI - Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API endpoint configuration
API_URL = "http://127.0.0.1:8000"

# Inject Custom CSS for Rich Premium Dark Mode & Glassmorphism Aesthetics
st.markdown(
    """
    <style>
    /* Global styles */
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161a25 100%);
        color: #e2e8f0;
    }
    
    /* Title and Header */
    .main-title {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem !important;
        font-weight: 800;
        margin-bottom: 0.2rem;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* KPI Card Container */
    .kpi-container {
        display: flex;
        flex-wrap: wrap;
        gap: 1.25rem;
        margin-bottom: 2rem;
    }
    
    /* KPI Card styling with Glassmorphism */
    .kpi-card {
        flex: 1;
        min-width: 200px;
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px rgba(255, 255, 255, 0.08) solid;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.25);
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    .kpi-card:hover {
        transform: translateY(-4px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .kpi-title {
        color: #94a3b8;
        font-size: 0.9rem;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    .kpi-val {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .kpi-delta-up {
        color: #10b981;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .kpi-delta-down {
        color: #f43f5e;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    /* Status indicator custom styling */
    .status-badge {
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .status-badge-ready {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .status-badge-pending {
        background-color: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .status-badge-running {
        background-color: rgba(59, 130, 246, 0.2);
        color: #3b82f6;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    /* Footer */
    .footer-text {
        text-align: center;
        color: #64748b;
        font-size: 0.85rem;
        margin-top: 4rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def call_api(endpoint: str, method: str = "GET", payload: dict = None) -> dict | None:
    """Helper to communicate with FastAPI backend and handle failure gracefully."""
    url = f"{API_URL}{endpoint}"
    try:
        if method == "POST":
            r = requests.post(url, json=payload, timeout=40)
        else:
            r = requests.get(url, timeout=40)

        if r.status_code == 200:
            return r.json()
        else:
            st.error(f"Backend API returned error (HTTP {r.status_code}): {r.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.warning(
            f"⚠️ Connection Error: Unable to connect to the backend server at {API_URL}.\n"
            f"Please verify that the FastAPI backend is running. Start it with:\n"
            f"`uvicorn api.main:app --reload --port 8000`"
        )
        return None


# HEADER SECTION
st.markdown('<div class="main-title">RetailSense AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">End-to-End Retail Analytics & 30-Day Sales Forecasting Platform</div>',
    unsafe_allow_html=True,
)

# SIDEBAR: ETL controls
st.sidebar.title("🛠️ Operations Control")

status_placeholder = st.sidebar.empty()
metrics_placeholder = st.sidebar.empty()
trigger_btn = st.sidebar.button("🚀 Run Medallion ETL & Forecasting", use_container_width=True)

# Fetch status
etl_status = call_api("/api/etl/status")

if etl_status:
    # Update status UI
    stat = etl_status.get("status", "pending_etl")

    if stat == "ready":
        badge_html = '<span class="status-badge status-badge-ready">Ready / Synced</span>'
    elif stat == "running":
        badge_html = '<span class="status-badge status-badge-running">Processing...</span>'
    else:
        badge_html = '<span class="status-badge status-badge-pending">Pending ETL</span>'

    status_placeholder.markdown(f"**Pipeline Status:** {badge_html}", unsafe_allow_html=True)

    # Show model evaluation metrics in sidebar if ready
    model_eval = etl_status.get("metrics")
    if model_eval:
        metrics_placeholder.markdown(
            f"""
            ---
            **🤖 Forecast Model Accuracy:**
            *   **RMSE:** `{model_eval.get('rmse', 0.0):.3f}`
            *   **MAE:** `{model_eval.get('mae', 0.0):.3f}`
            *   **R² Score:** `{model_eval.get('r2', 0.0):.3f}`
            """
        )

# Trigger ETL if button pressed
if trigger_btn:
    st.sidebar.info("Starting Spark job...")
    res = call_api("/api/etl/run", method="POST")
    if res:
        st.sidebar.success("ETL launched successfully!")
        st.toast("Pipeline run started in the background. Please wait 1-2 minutes...")
        time.sleep(1)
        st.rerun()

# RENDER MAIN CONTENT TABS
if not etl_status or etl_status.get("status") == "pending_etl":
    st.info(
        "👋 Welcome! The retail analytics database is empty. "
        "Please click the **'Run Medallion ETL & Forecasting'** button in the sidebar "
        "to run the PySpark pipeline, compute lag/rolling features, train the XGBoost model, "
        "and unlock full dashboard analytics."
    )
elif etl_status.get("status") == "running":
    st.info("⏳ The PySpark Medallion ETL & model training pipeline is currently processing in the background. This page will refresh automatically...")
    time.sleep(5)
    st.rerun()
else:
    # ETL IS READY, LOAD DASHBOARD
    tab_overview, tab_sales, tab_products, tab_forecast, tab_ai = st.tabs(
        [
            "📊 Executive Summary",
            "📈 Sales Trends",
            "🛒 Product & Store Analysis",
            "🔮 Sales Forecasting",
            "💬 AI Retail Assistant",
        ]
    )

    # Fetch KPIs from API
    kpi_data = call_api("/api/analytics/kpis")

    if kpi_data:
        # ---- TAB 1: EXECUTIVE SUMMARY ----
        with tab_overview:
            # Cards
            growth_delta = f"+{kpi_data['growth_rate_wow']:.1f}%" if kpi_data["growth_rate_wow"] >= 0 else f"{kpi_data['growth_rate_wow']:.1f}%"
            delta_class = "kpi-delta-up" if kpi_data["growth_rate_wow"] >= 0 else "kpi-delta-down"

            st.markdown(
                f"""
                <div class="kpi-container">
                    <div class="kpi-card">
                        <div class="kpi-title">Total Revenue</div>
                        <div class="kpi-val">${kpi_data['total_revenue']:,.2f}</div>
                        <div class="kpi-delta-up">Cumulative sales</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Total Units Sold</div>
                        <div class="kpi-val">{kpi_data['total_units_sold']:,}</div>
                        <div class="kpi-delta-up">Products shipped</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Average Item Price</div>
                        <div class="kpi-val">${kpi_data['average_selling_price']:.2f}</div>
                        <div class="kpi-delta-up">Global retail ASP</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Growth Rate (WoW)</div>
                        <div class="kpi-val">{growth_delta}</div>
                        <div class="{delta_class}">vs previous week</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Columns for plots
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("State-Wise Cumulative Revenue")
                df_state = pd.DataFrame(kpi_data["states"])
                if not df_state.empty:
                    fig, ax = plt.subplots(figsize=(6, 4))
                    fig.patch.set_facecolor("none")
                    ax.set_facecolor("none")
                    sns.barplot(
                        x="state_id",
                        y="total_revenue",
                        data=df_state,
                        palette="viridis",
                        ax=ax,
                    )
                    ax.set_xlabel("State", color="#94a3b8")
                    ax.set_ylabel("Revenue ($)", color="#94a3b8")
                    ax.tick_params(colors="#94a3b8")
                    ax.spines["bottom"].set_color("#475569")
                    ax.spines["left"].set_color("#475569")
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    plt.tight_layout()
                    st.pyplot(fig)

            with col2:
                st.subheader("Category Revenue Breakdown")
                df_cat = pd.DataFrame(kpi_data["categories"])
                if not df_cat.empty:
                    fig, ax = plt.subplots(figsize=(6, 4))
                    fig.patch.set_facecolor("none")
                    ax.set_facecolor("none")
                    colors = ["#38bdf8", "#818cf8", "#c084fc"]
                    ax.pie(
                        df_cat["total_revenue"],
                        labels=df_cat["cat_id"],
                        autopct="%1.1f%%",
                        colors=colors,
                        textprops={"color": "#e2e8f0"},
                        wedgeprops={"edgecolor": "#1e293b", "linewidth": 2},
                    )
                    plt.tight_layout()
                    st.pyplot(fig)

        # ---- TAB 2: SALES TRENDS ----
        with tab_sales:
            st.subheader("Historical vs Predict Daily Units Trend")
            forecast_data = call_api("/api/forecast/predict")

            if forecast_data:
                df_points = pd.DataFrame(forecast_data["points"])
                if not df_points.empty:
                    df_points["date"] = pd.to_datetime(df_points["date"])

                    fig, ax = plt.subplots(figsize=(10, 4.5))
                    fig.patch.set_facecolor("none")
                    ax.set_facecolor("none")

                    # Filter history & forecast
                    df_hist_pts = df_points[df_points["type"] == "Historical"]
                    df_fore_pts = df_points[df_points["type"] == "Forecasted"]

                    ax.plot(
                        df_hist_pts["date"],
                        df_hist_pts["sales"],
                        color="#6366f1",
                        linewidth=2.5,
                        label="Historical Sales",
                    )
                    ax.plot(
                        df_fore_pts["date"],
                        df_fore_pts["sales"],
                        color="#f43f5e",
                        linestyle="--",
                        linewidth=2.5,
                        label="Projected 30-Day Forecast",
                    )

                    ax.set_ylabel("Daily Units Sold", color="#94a3b8")
                    ax.tick_params(colors="#94a3b8")
                    ax.spines["bottom"].set_color("#475569")
                    ax.spines["left"].set_color("#475569")
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    ax.legend(facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0")
                    plt.tight_layout()
                    st.pyplot(fig)

            # Store rankings
            st.subheader("Store Revenue Rankings")
            df_store = pd.DataFrame(kpi_data["stores"])
            if not df_store.empty:
                df_store_sorted = df_store.sort_values("total_revenue", ascending=False)
                fig, ax = plt.subplots(figsize=(10, 3.5))
                fig.patch.set_facecolor("none")
                ax.set_facecolor("none")
                sns.barplot(
                    x="total_revenue",
                    y="store_id",
                    data=df_store_sorted,
                    palette="magma",
                    orient="h",
                    ax=ax,
                )
                ax.set_xlabel("Revenue ($)", color="#94a3b8")
                ax.set_ylabel("Store ID", color="#94a3b8")
                ax.tick_params(colors="#94a3b8")
                ax.spines["bottom"].set_color("#475569")
                ax.spines["left"].set_color("#475569")
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                plt.tight_layout()
                st.pyplot(fig)

        # ---- TAB 3: PRODUCT & STORE ANALYTICS ----
        with tab_products:
            st.subheader("Retail Performance Deep-Dive")

            col_p1, col_p2 = st.columns(2)

            with col_p1:
                st.write("🏆 **Top 5 Performing Products (by Revenue)**")
                df_top_prod = pd.DataFrame(kpi_data["top_products"])
                if not df_top_prod.empty:
                    st.dataframe(
                        df_top_prod[["item_id", "cat_id", "total_units", "total_revenue"]].rename(
                            columns={
                                "item_id": "Item ID",
                                "cat_id": "Category",
                                "total_units": "Units Sold",
                                "total_revenue": "Revenue ($)",
                            }
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

            with col_p2:
                st.write("⚠️ **Lowest 5 Performing Products (by Revenue)**")
                df_worst_prod = pd.DataFrame(kpi_data["worst_products"])
                if not df_worst_prod.empty:
                    st.dataframe(
                        df_worst_prod[["item_id", "cat_id", "total_units", "total_revenue"]].rename(
                            columns={
                                "item_id": "Item ID",
                                "cat_id": "Category",
                                "total_units": "Units Sold",
                                "total_revenue": "Revenue ($)",
                            }
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

        # ---- TAB 4: SALES FORECASTING ----
        with tab_forecast:
            st.subheader("Recursive 30-Day Project Details")

            if forecast_data:
                df_pts = pd.DataFrame(forecast_data["points"])
                df_fore_pts = df_pts[df_pts["type"] == "Forecasted"]

                if not df_fore_pts.empty:
                    f_revenue = df_fore_pts["revenue"].sum()
                    f_units = df_fore_pts["sales"].sum()

                    c_f1, c_f2, c_f3 = st.columns(3)
                    with c_f1:
                        st.metric("Forecasted Total Revenue", f"${f_revenue:,.2f}")
                    with c_f2:
                        st.metric("Forecasted Units Sold", f"{int(f_units):,}")
                    with c_f3:
                        st.metric("Average Daily Units", f"{f_units/30:.1f} units/day")

                    # Detailed forecast graph
                    fig, ax = plt.subplots(figsize=(10, 4.5))
                    fig.patch.set_facecolor("none")
                    ax.set_facecolor("none")

                    ax.plot(
                        df_fore_pts["date"],
                        df_fore_pts["sales"],
                        color="#f43f5e",
                        marker="o",
                        linewidth=2.5,
                        label="Daily Forecast",
                    )
                    ax.fill_between(
                        df_fore_pts["date"],
                        df_fore_pts["sales"] * 0.9,
                        df_fore_pts["sales"] * 1.1,
                        color="#f43f5e",
                        alpha=0.15,
                        label="90% Confidence Interval",
                    )

                    ax.set_ylabel("Units Forecasted", color="#94a3b8")
                    ax.tick_params(colors="#94a3b8")
                    ax.spines["bottom"].set_color("#475569")
                    ax.spines["left"].set_color("#475569")
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    ax.legend(facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0")
                    plt.tight_layout()
                    st.pyplot(fig)
                else:
                    st.warning("Forecast details not available. Please rerun ETL.")

        # ---- TAB 5: AI RETAIL ASSISTANT ----
        with tab_ai:
            st.subheader("💬 AI Retail Assistant (Grok / Groq LLM)")
            st.write(
                "Ask natural language questions about store performance, categories, sales trends, "
                "or 30-day inventory and forecasting recommendations."
            )

            # Chat state manager
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Display past messages
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Input field
            if prompt := st.chat_input("What would you like to ask the Retail Assistant?"):
                with st.chat_message("user"):
                    st.markdown(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})

                # API Call to /api/chat
                with st.chat_message("assistant"):
                    with st.spinner("AI Assistant is analyzing KPI tables and generating answer..."):
                        res = call_api("/api/chat", method="POST", payload={"message": prompt})
                        if res:
                            answer = res["response"]
                            st.markdown(answer)
                            st.session_state.messages.append({"role": "assistant", "content": answer})
                        else:
                            st.error("Failed to generate AI insights.")

            # Quick Prompt Buttons
            st.write("")
            st.write("**💡 Suggested Prompts:**")
            quick_cols = st.columns(4)
            quick_prompts = [
                "Suggest inventory actions for Foods category.",
                "Explain the forecast results for the next 30 days.",
                "Which category has highest revenue, and why?",
                "Provide a brief executive summary report.",
            ]

            for i, p in enumerate(quick_prompts):
                with quick_cols[i % 4]:
                    if st.button(p, key=f"q_{i}", use_container_width=True):
                        # Force submit quick prompt
                        st.session_state.messages.append({"role": "user", "content": p})
                        with st.spinner("AI is thinking..."):
                            res = call_api("/api/chat", method="POST", payload={"message": p})
                            if res:
                                st.session_state.messages.append({"role": "assistant", "content": res["response"]})
                        st.rerun()

st.markdown('<div class="footer-text">RetailSense AI Platform • Powered by Azure Databricks, PySpark, Delta Lake & Grok LLM</div>', unsafe_allow_html=True)
