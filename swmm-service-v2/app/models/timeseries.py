"""
Timeseries data models for SWMM Service v2
Extracted from main_old.py
"""

from pydantic import BaseModel
from typing import Dict, List, Any


class TimeseriesInput(BaseModel):
    """Timeseries input model (from main_old.py)"""
    rain: Dict[str, float]  # "MM/DD/YYYY HH:MM" -> mm/hr
    inflow_dautieng: Dict[str, float]  # m3/s
    inflow_trian: Dict[str, float]  # m3/s
    tide: Dict[str, float]  # m


class SimulationInput(BaseModel):
    """Simulation input model (from main_old.py)"""
    simulation_name: str
    start_date: str
    end_date: str
    time_step: int
    timeseries: Dict[str, List[Dict[str, Any]]]
