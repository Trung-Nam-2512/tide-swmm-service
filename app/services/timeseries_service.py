"""
Timeseries service for SWMM Service v2
Extracted from main_old.py
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional
from ..models.timeseries import TimeseriesInput
from .tide_api_service import get_tide_timeseries

logger = logging.getLogger(__name__)


def interpolate_ts(ts_dict: Dict[str, float]) -> Dict[str, float]:
    """
    Interpolate timeseries data (from main_old.py)
    
    Args:
        ts_dict: Dictionary of time-value pairs
        
    Returns:
        Interpolated timeseries dictionary
    """
    if not ts_dict:
        return {}
    
    times = sorted([datetime.strptime(t, "%m/%d/%Y %H:%M") for t in ts_dict.keys()])
    values = [ts_dict[times[i].strftime("%m/%d/%Y %H:%M")] for i in range(len(times))]
    full_times = pd.date_range(times[0], times[-1], freq="H")
    interp_values = np.interp([t.timestamp() for t in full_times], [t.timestamp() for t in times], values)
    return {full_times[i].strftime("%m/%d/%Y %H:%M"): interp_values[i] for i in range(len(full_times))}


def generate_forecast_scenarios(start_date: str, 
                               end_date: str, 
                               rain_scenario: Optional[Dict[str, float]] = None,
                               inflow_scenario: Optional[Dict[str, float]] = None,
                               tide_scenario: Optional[Dict[str, float]] = None) -> TimeseriesInput:
    """
    Generate forecast scenarios (from main_old.py)
    
    Args:
        start_date: Start date in MM/DD/YYYY format
        end_date: End date in MM/DD/YYYY format
        rain_scenario: Custom rain data
        inflow_scenario: Custom inflow data
        tide_scenario: Custom tide data
        
    Returns:
        TimeseriesInput object
    """
    # Tạo date range
    start_dt = datetime.strptime(start_date, "%m/%d/%Y")
    end_dt = datetime.strptime(end_date, "%m/%d/%Y")
    date_range = pd.date_range(start_dt, end_dt, freq="H")
    
    # Tạo rain scenario
    if rain_scenario:
        rain_data = interpolate_ts(rain_scenario)
    else:
        # Dự báo mưa dựa trên pattern lịch sử
        rain_data = {dt.strftime("%m/%d/%Y %H:%M"): 
                    max(0, 3 * np.sin(2 * np.pi * i / 24) + 2 + np.random.normal(0, 1)) 
                    for i, dt in enumerate(date_range)}
    
    # Tạo inflow scenario
    if inflow_scenario:
        inflow_dt_data = interpolate_ts(inflow_scenario)
        inflow_ta_data = interpolate_ts(inflow_scenario)
    else:
        # Dự báo lưu lượng ổn định
        inflow_dt_data = {dt.strftime("%m/%d/%Y %H:%M"): 24.0 for dt in date_range}
        inflow_ta_data = {dt.strftime("%m/%d/%Y %H:%M"): 800.0 for dt in date_range}
    
    # Tạo tide scenario
    if tide_scenario:
        tide_data = interpolate_ts(tide_scenario)
    else:
        # Sử dụng API thủy triều thực từ tide.nguyentrungnam.com
        logger.info("Fetching real tide data from API...")
        tide_data = get_tide_timeseries(start_date, end_date)
    
    return TimeseriesInput(
        rain=rain_data,
        inflow_dautieng=inflow_dt_data,
        inflow_trian=inflow_ta_data,
        tide=tide_data
    )
