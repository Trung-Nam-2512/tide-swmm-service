"""
Forecast schemas for SWMM service
"""

from pydantic import BaseModel
from typing import List, Optional, Dict


class ForecastLevel(BaseModel):
    """Schema for forecast level at specific time"""
    time: str  # "MM/DD/YYYY HH:MM"
    level: float  # m


class NodeInfo(BaseModel):
    """Schema for node information"""
    node_id: str
    node_type: str  # "JUNCTION", "STORAGE", "OUTFALL"
    x_coordinate: float
    y_coordinate: float
    invert_elevation: float  # m
    ground_elevation: float  # m
    max_depth: float  # m
    initial_depth: float  # m
    surface_depth: float  # m
    ponded_area: float  # m²


class WaterLevelForecast(BaseModel):
    """Schema for water level forecast"""
    node_id: str
    node_info: NodeInfo
    current_level: float  # m
    forecast_levels: List[ForecastLevel]  # List of time-level pairs
    max_forecast_level: float  # m
    flood_risk: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    flood_probability: float  # 0.0 - 1.0


class ForecastRequest(BaseModel):
    """Schema for forecast request"""
    start_date: str  # "MM/DD/YYYY"
    end_date: str    # "MM/DD/YYYY"
    rain_scenario: Optional[Dict[str, float]] = None  # Custom rain data
    inflow_scenario: Optional[Dict[str, float]] = None  # Custom inflow data
    tide_scenario: Optional[Dict[str, float]] = None  # Custom tide data
    nodes_filter: Optional[List[str]] = None  # Specific nodes to forecast
