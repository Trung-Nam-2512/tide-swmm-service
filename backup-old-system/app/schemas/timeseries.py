"""
Timeseries schemas for SWMM service
"""

from pydantic import BaseModel
from typing import Dict, List, Any


class TimeseriesInput(BaseModel):
    """Input schema for timeseries data"""
    rain: Dict[str, float]  # "MM/DD/YYYY HH:MM" -> mm/hr
    inflow_dautieng: Dict[str, float]  # m3/s
    inflow_trian: Dict[str, float]  # m3/s
    tide: Dict[str, float]  # m


class SimulationInput(BaseModel):
    """Input schema for custom simulation"""
    simulation_name: str
    start_date: str
    end_date: str
    time_step: int
    timeseries: Dict[str, List[Dict[str, Any]]]
