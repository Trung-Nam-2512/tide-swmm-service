"""
Tide API Service for SWMM Service v2
Fetches real tide data from tide.nguyentrungnam.com API
"""

import logging
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from ..config.settings import settings

logger = logging.getLogger(__name__)

# API Configuration
TIDE_API_BASE_URL = "https://tide.nguyentrungnam.com/api/v1"
TIDE_API_ENDPOINT = "/get-tide-forecast-data"
TIDE_LOCATION = "VUNGTAU"

def fetch_tide_data(from_date: str, to_date: str) -> List[Dict]:
    """
    Fetch tide data from real API
    
    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
        
    Returns:
        List of tide data records
    """
    try:
        url = f"{TIDE_API_BASE_URL}{TIDE_API_ENDPOINT}"
        params = {
            "from": from_date,
            "to": to_date,
            "location": TIDE_LOCATION
        }
        
        logger.info(f"Fetching tide data from API: {url}")
        logger.info(f"Parameters: {params}")
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("success", False):
            raise Exception(f"API returned error: {data}")
            
        tide_records = data.get("data", [])
        logger.info(f"Successfully fetched {len(tide_records)} tide records")
        
        return tide_records
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        raise Exception(f"Failed to fetch tide data: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing tide data: {str(e)}")
        raise Exception(f"Error processing tide data: {str(e)}")

def convert_tide_data_to_timeseries(tide_records: List[Dict]) -> Dict[str, float]:
    """
    Convert API tide data to timeseries format with timezone conversion
    
    Args:
        tide_records: List of tide records from API
        
    Returns:
        Dictionary of time-value pairs for SWMM timeseries (Vietnam timezone UTC+7)
    """
    from datetime import timedelta
    import pytz
    
    timeseries = {}
    
    for record in tide_records:
        try:
            # Parse date from API
            date_str = record.get("date", "")
            if not date_str:
                continue
                
            # Convert from ISO format (UTC) to Vietnam timezone (UTC+7)
            dt_utc = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            
            # Add 7 hours to convert from UTC to Vietnam time
            dt_vietnam = dt_utc + timedelta(hours=7)
            
            # Format for SWMM timeseries
            swmm_time = dt_vietnam.strftime("%m/%d/%Y %H:%M")
            
            # Get tide value and convert from cm to m
            tide_cm = record.get("tide", 0)
            tide_m = tide_cm / 100.0  # Convert cm to m
            
            timeseries[swmm_time] = tide_m
            
        except Exception as e:
            logger.warning(f"Error processing tide record {record}: {str(e)}")
            continue
    
    logger.info(f"Converted {len(timeseries)} tide records to timeseries format (Vietnam timezone)")
    return timeseries

def get_tide_timeseries(start_date: str, end_date: str) -> Dict[str, float]:
    """
    Get tide timeseries data for SWMM simulation with timezone adjustment
    
    Args:
        start_date: Start date in MM/DD/YYYY format (Vietnam time)
        end_date: End date in MM/DD/YYYY format (Vietnam time)
        
    Returns:
        Dictionary of time-value pairs for SWMM timeseries (Vietnam time)
    """
    try:
        from datetime import timedelta
        
        # Convert dates to API format
        start_dt = datetime.strptime(start_date, "%m/%d/%Y")
        end_dt = datetime.strptime(end_date, "%m/%d/%Y")
        
        # Adjust API date range: lùi lại 1 ngày để lấy đủ 7 giờ dữ liệu trước 00h
        # Vì UTC 00h = Vietnam 07h, nên cần lấy từ ngày trước để có đủ dữ liệu
        api_start_dt = start_dt - timedelta(days=1)
        api_end_dt = end_dt
        
        api_start = api_start_dt.strftime("%Y-%m-%d")
        api_end = api_end_dt.strftime("%Y-%m-%d")
        
        logger.info(f"Requesting tide data from API: {api_start} to {api_end}")
        logger.info(f"Vietnam time range: {start_date} to {end_date}")
        
        # Fetch data from API
        tide_records = fetch_tide_data(api_start, api_end)
        
        # Convert to timeseries format (with timezone conversion)
        timeseries = convert_tide_data_to_timeseries(tide_records)
        
        if not timeseries:
            logger.warning("No tide data received from API, using fallback simulation")
            return generate_fallback_tide_data(start_date, end_date)
        
        # Filter timeseries to only include the requested Vietnam time range
        filtered_timeseries = {}
        start_vietnam = datetime.strptime(start_date, "%m/%d/%Y")
        end_vietnam = datetime.strptime(end_date, "%m/%d/%Y")
        
        for time_str, value in timeseries.items():
            time_dt = datetime.strptime(time_str, "%m/%d/%Y %H:%M")
            if start_vietnam <= time_dt <= end_vietnam:
                filtered_timeseries[time_str] = value
        
        logger.info(f"Filtered to {len(filtered_timeseries)} data points for Vietnam time range")
        return filtered_timeseries
        
    except Exception as e:
        logger.error(f"Failed to get tide timeseries: {str(e)}")
        logger.info("Falling back to simulated tide data")
        return generate_fallback_tide_data(start_date, end_date)

def generate_fallback_tide_data(start_date: str, end_date: str) -> Dict[str, float]:
    """
    Generate fallback tide data if API fails
    
    Args:
        start_date: Start date in MM/DD/YYYY format
        end_date: End date in MM/DD/YYYY format
        
    Returns:
        Dictionary of simulated tide data
    """
    import numpy as np
    
    start_dt = datetime.strptime(start_date, "%m/%d/%Y")
    end_dt = datetime.strptime(end_date, "%m/%d/%Y")
    date_range = pd.date_range(start_dt, end_dt, freq="H")
    
    # Generate simulated tide data (fallback)
    tide_data = {
        dt.strftime("%m/%d/%Y %H:%M"): 
        1.5 * np.sin(2 * np.pi * i / 12.4) + 1.0 + np.random.normal(0, 0.1)
        for i, dt in enumerate(date_range)
    }
    
    logger.info(f"Generated {len(tide_data)} fallback tide data points")
    return tide_data
