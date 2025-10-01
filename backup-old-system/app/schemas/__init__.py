"""
Schemas module for SWMM service
Contains all Pydantic models for request/response validation
"""

from .timeseries import TimeseriesInput, SimulationInput
from .forecast import ForecastLevel, NodeInfo, WaterLevelForecast, ForecastRequest
from .response import HealthResponse, WaterLevelResponse, NodeListResponse

__all__ = [
    "TimeseriesInput",
    "SimulationInput", 
    "ForecastLevel",
    "NodeInfo",
    "WaterLevelForecast",
    "ForecastRequest",
    "HealthResponse",
    "WaterLevelResponse",
    "NodeListResponse"
]
