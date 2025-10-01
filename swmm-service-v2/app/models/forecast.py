"""
Forecast data models for SWMM Service v2
Extracted from main_old.py
"""

from pydantic import BaseModel
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .node import NodeInfo


class ForecastLevel(BaseModel):
    """Forecast level model (from main_old.py)"""
    time: str  # "MM/DD/YYYY HH:MM"
    level: float  # m


class WaterLevelForecast(BaseModel):
    """Water level forecast model (from main_old.py)"""
    node_id: str
    node_info: 'NodeInfo'  # Forward reference
    current_level: float  # m
    forecast_levels: List[ForecastLevel]  # List of time-level pairs
    max_forecast_level: float  # m
    flood_risk: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    flood_probability: float  # 0.0 - 1.0
