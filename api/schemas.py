"""
Pydantic schemas for the FastAPI backend.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """User request query for the AI Retail Assistant."""
    message: str = Field(..., example="Suggest inventory actions for Foods category.")
    session_id: Optional[str] = Field(default="default-session", example="session-123")


class ChatResponse(BaseModel):
    """Assistant response back to the user."""
    response: str
    session_id: str
    latency_ms: float


class ETLStatusResponse(BaseModel):
    """Detailed status of the Medallion Delta Lake architecture and trained model."""
    status: str
    tables_exist: Dict[str, bool]
    model_exists: bool
    metrics: Optional[Dict[str, float]] = None


class StorePerformance(BaseModel):
    """Store level performance metrics."""
    store_id: str
    state_id: str
    total_units: int
    total_revenue: float
    avg_sell_price: float


class ProductPerformance(BaseModel):
    """Product level performance metrics."""
    item_id: str
    dept_id: str
    cat_id: str
    total_units: int
    total_revenue: float


class CategoryPerformance(BaseModel):
    """Category level performance metrics."""
    cat_id: str
    total_units: int
    total_revenue: float


class StatePerformance(BaseModel):
    """State level performance metrics."""
    state_id: str
    total_units: int
    total_revenue: float


class MonthlySalesPerformance(BaseModel):
    """Monthly historical sales performance."""
    year: int
    month: int
    total_units: int
    total_revenue: float


class KPIsResponse(BaseModel):
    """Aggregated KPIs for the Executive Dashboard."""
    total_revenue: float
    total_units_sold: int
    average_selling_price: float
    growth_rate_wow: float
    active_products: int
    active_stores: int
    stores: List[StorePerformance]
    categories: List[CategoryPerformance]
    states: List[StatePerformance]
    top_products: List[ProductPerformance]
    worst_products: List[ProductPerformance]


class ForecastPoint(BaseModel):
    """Forecast and historical data coordinates for plotting."""
    date: str
    type: str  # "Historical" or "Forecasted"
    sales: float
    revenue: float
    cat_id: Optional[str] = None
    store_id: Optional[str] = None


class ForecastResponse(BaseModel):
    """Full list of historical data points and forecasted data points."""
    points: List[ForecastPoint]
    metrics: Optional[Dict[str, float]] = None
