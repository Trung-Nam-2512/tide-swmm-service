"""
Real data service for fetching external API data
"""

import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)


class RealDataService:
    """Service for fetching real-time data from external APIs"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"  # Backend API URL
        self.tide_api_url = "https://tide.nguyentrungnam.com/api/v1"  # Vũng Tàu Tide API
        self.timeout = 30.0
    
    async def fetch_vung_tau_tide_data(self, 
                                      start_date: datetime, 
                                      end_date: datetime) -> Dict[str, Any]:
        """
        Fetch Vũng Tàu tide data from external API
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            API response data
        """
        try:
            # Format dates for API
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            url = f"{self.tide_api_url}/get-tide-forecast-data"
            params = {
                "from": start_str,
                "to": end_str,
                "location": "VUNGTAU"
            }
            
            logger.info(f"Fetching Vũng Tàu tide data from {url} with params: {params}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Successfully fetched {len(data.get('data', []))} tide data points")
                return data
                
        except Exception as e:
            logger.error(f"Error fetching Vũng Tàu tide data: {str(e)}")
            return {"data": []}
    
    def convert_tide_data_to_timeseries(self, tide_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Convert API tide data to SWMM timeseries format
        
        Args:
            tide_data: API response data
            
        Returns:
            Timeseries dictionary in SWMM format
        """
        timeseries = {}
        try:
            data_array = tide_data.get("data", [])
            for item in data_array:
                if "date" in item and "tide" in item:
                    from datetime import datetime
                    iso_date = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
                    
                    # Use UTC time directly without conversion
                    time_str = iso_date.strftime("%m/%d/%Y %H:%M")
                    
                    # Convert tide from cm to meters
                    tide_level = item["tide"] / 100.0
                    
                    timeseries[time_str] = tide_level
            logger.info(f"Converted {len(timeseries)} Vũng Tàu tide data points from API")
        except Exception as e:
            logger.error(f"Error converting tide data to timeseries: {str(e)}")
        return timeseries
    
    async def get_real_timeseries_data(self, 
                                     start_date: str, 
                                     end_date: str) -> Dict[str, Any]:
        """
        Get real timeseries data for all sources
        
        Args:
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            
        Returns:
            Dictionary with all timeseries data
        """
        try:
            start_dt = datetime.strptime(start_date, "%m/%d/%Y")
            end_dt = datetime.strptime(end_date, "%m/%d/%Y")
            
            # Fetch Vũng Tàu tide data
            tide_data = await self.fetch_vung_tau_tide_data(start_dt, end_dt)
            tide_timeseries = self.convert_tide_data_to_timeseries(tide_data)
            
            # Generate hourly time series for the FULL date range (including missing hours)
            full_date_range = pd.date_range(start_dt, end_dt, freq="h")
            
            hdt_timeseries = {}
            ta_timeseries = {}
            
            for current_date in full_date_range:
                time_str = current_date.strftime("%m/%d/%Y %H:%M")
                hdt_timeseries[time_str] = 24.0  # Fixed constant for Hồ Dầu Tiếng (m³/s)
                ta_timeseries[time_str] = 800.0  # Fixed constant for Hồ Trị An (m³/s)
            
            return {
                "tide": tide_timeseries,
                "inflow_dautieng": hdt_timeseries,
                "inflow_trian": ta_timeseries,
                "rain": {}  # Will use synthetic data for rain
            }
        except Exception as e:
            logger.error(f"Error getting real timeseries data: {str(e)}")
            return {
                "tide": {},
                "inflow_dautieng": {},
                "inflow_trian": {},
                "rain": {}
            }