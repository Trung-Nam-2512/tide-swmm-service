"""
Timeseries utilities for SWMM service
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TimeseriesUtils:
    """Utility class for timeseries operations"""
    
    @staticmethod
    def interpolate_timeseries(ts_dict: Dict[str, float]) -> Dict[str, float]:
        """
        Interpolate timeseries data to fill missing values
        
        Args:
            ts_dict: Dictionary with time as key and value as value
            
        Returns:
            Interpolated timeseries dictionary
        """
        if not ts_dict:
            return {}
            
        try:
            # Parse times and sort them
            times = sorted([datetime.strptime(t, "%m/%d/%Y %H:%M") for t in ts_dict.keys()])
            values = [ts_dict[times[i].strftime("%m/%d/%Y %H:%M")] for i in range(len(times))]
            
            # Create full time range with hourly frequency
            full_times = pd.date_range(times[0], times[-1], freq="h", inclusive="left")
            
            # Interpolate values
            interp_values = np.interp(
                [t.timestamp() for t in full_times], 
                [t.timestamp() for t in times], 
                values
            )
            
            # Return as dictionary
            return {
                full_times[i].strftime("%m/%d/%Y %H:%M"): interp_values[i] 
                for i in range(len(full_times))
            }
            
        except Exception as e:
            logger.error(f"Error interpolating timeseries: {str(e)}")
            return ts_dict
    
    @staticmethod
    def generate_rain_scenario(start_date: str, end_date: str, 
                              custom_data: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Generate rain scenario data
        
        Args:
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            custom_data: Custom rain data if provided
            
        Returns:
            Rain scenario dictionary
        """
        if custom_data:
            return TimeseriesUtils.interpolate_timeseries(custom_data)
        
        # Generate synthetic rain data
        start_dt = datetime.strptime(start_date, "%m/%d/%Y")
        end_dt = datetime.strptime(end_date, "%m/%d/%Y")
        # Include end_dt by adding 1 day to ensure complete coverage
        date_range = pd.date_range(start_dt, end_dt + timedelta(days=1), freq="h", inclusive="left")
        
        return {
            dt.strftime("%m/%d/%Y %H:%M"): 
            max(0, 3 * np.sin(2 * np.pi * i / 24) + 2 + np.random.normal(0, 1)) 
            for i, dt in enumerate(date_range)
        }
    
    @staticmethod
    def generate_inflow_scenario(start_date: str, end_date: str, 
                                custom_data: Optional[Dict[str, float]] = None,
                                default_value: float = 24.0) -> Dict[str, float]:
        """
        Generate inflow scenario data
        
        Args:
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            custom_data: Custom inflow data if provided
            default_value: Default inflow value
            
        Returns:
            Inflow scenario dictionary
        """
        if custom_data:
            return TimeseriesUtils.interpolate_timeseries(custom_data)
        
        # Generate constant inflow data
        start_dt = datetime.strptime(start_date, "%m/%d/%Y")
        end_dt = datetime.strptime(end_date, "%m/%d/%Y")
        # Include end_dt by adding 1 day to ensure complete coverage
        date_range = pd.date_range(start_dt, end_dt + timedelta(days=1), freq="h", inclusive="left")
        
        return {
            dt.strftime("%m/%d/%Y %H:%M"): default_value 
            for dt in date_range
        }
    
    @staticmethod
    def generate_tide_scenario(start_date: str, end_date: str, 
                              custom_data: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Generate tide scenario data
        
        Args:
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            custom_data: Custom tide data if provided
            
        Returns:
            Tide scenario dictionary
        """
        if custom_data:
            return TimeseriesUtils.interpolate_timeseries(custom_data)
        
        # Generate synthetic tide data based on tidal cycle
        start_dt = datetime.strptime(start_date, "%m/%d/%Y")
        end_dt = datetime.strptime(end_date, "%m/%d/%Y")
        # Include end_dt by adding 1 day to ensure complete coverage
        date_range = pd.date_range(start_dt, end_dt + timedelta(days=1), freq="h", inclusive="left")
        
        return {
            dt.strftime("%m/%d/%Y %H:%M"): 
            1.5 * np.sin(2 * np.pi * i / 12.4) + 1.0 + np.random.normal(0, 0.1)
            for i, dt in enumerate(date_range)
        }