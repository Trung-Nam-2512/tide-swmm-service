"""
Request data models for SWMM Service v2
Extracted from main_old.py
"""

from pydantic import BaseModel
from typing import Dict, List, Optional


class ForecastRequest(BaseModel):
    """Forecast request model (from main_old.py)"""
    start_date: str  # "MM/DD/YYYY"
    end_date: str    # "MM/DD/YYYY"
    rain_scenario: Optional[Dict[str, float]] = None  # Custom rain data
    inflow_scenario: Optional[Dict[str, float]] = None  # Custom inflow data
    tide_scenario: Optional[Dict[str, float]] = None  # Custom tide data
    nodes_filter: Optional[List[str]] = None  # Specific nodes to forecast
