"""
Forecast service for SWMM Service v2
Extracted from main_old.py
"""

import logging
from typing import Dict, List, Any
from fastapi import HTTPException
from ..models.forecast import WaterLevelForecast, ForecastLevel
from ..models.node import NodeInfo
from ..utils.swmm_utils import get_node_detailed_info
from ..utils.math_utils import calculate_flood_risk
from ..config.settings import settings

logger = logging.getLogger(__name__)


def create_water_level_forecast(node_id: str, 
                               simulation_results: List[Dict], 
                               current_time: str = None) -> WaterLevelForecast:
    """
    Create water level forecast for a specific node (from main_old.py)
    
    Args:
        node_id: Node ID to forecast
        simulation_results: Results from SWMM simulation
        current_time: Current time (optional)
        
    Returns:
        WaterLevelForecast object
    """
    # Tìm node trong kết quả simulation
    node_data = None
    for result in simulation_results:
        if result["node"] == node_id:
            node_data = result
            break
    
    if not node_data:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found in simulation results")
    
    time_series = node_data["time_series"]
    if not time_series:
        raise HTTPException(status_code=400, detail=f"No time series data for node {node_id}")
    
    # Lấy thông tin chi tiết của node
    node_info = get_node_detailed_info(node_id, settings.get_inp_file_path())
    
    # Lấy mực nước hiện tại (giờ cuối cùng)
    current_depth = time_series[-1]["depth"] if time_series else 0.0
    current_level = current_depth + node_info.invert_elevation  # Water level = depth + invert elevation
    
    # Tạo forecast levels (chuyển đổi depth thành water level)
    forecast_levels = []
    for ts in time_series:
        water_level = ts["depth"] + node_info.invert_elevation
        forecast_levels.append(ForecastLevel(
            time=ts["time"],
            level=water_level  # Mực nước thực tế
        ))
    
    max_depth = node_data["max_depth_m"]
    max_forecast_level = max_depth + node_info.invert_elevation  # Mực nước tối đa thực tế
    
    # Tính nguy cơ ngập lụt với thông tin địa hình
    flood_risk, flood_probability = calculate_flood_risk(
        max_depth, node_info.invert_elevation, node_info.ground_elevation, node_info.max_depth
    )
    
    return WaterLevelForecast(
        node_id=node_id,
        node_info=node_info,
        current_level=current_level,
        forecast_levels=forecast_levels,
        max_forecast_level=max_forecast_level,
        flood_risk=flood_risk,
        flood_probability=flood_probability
    )
