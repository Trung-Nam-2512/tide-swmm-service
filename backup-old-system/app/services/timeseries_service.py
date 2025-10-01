"""
Timeseries service for SWMM service
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from ..schemas.timeseries import TimeseriesInput
from ..utils.timeseries_utils import TimeseriesUtils
from .real_data_service import RealDataService

logger = logging.getLogger(__name__)


class TimeseriesService:
    """Service for timeseries operations"""
    
    def __init__(self):
        self.timeseries_utils = TimeseriesUtils()
        self.real_data_service = RealDataService()
    
    async def generate_forecast_scenarios(self, 
                                        start_date: str, 
                                        end_date: str, 
                                        rain_scenario: Optional[Dict[str, float]] = None,
                                        inflow_scenario: Optional[Dict[str, float]] = None,
                                        tide_scenario: Optional[Dict[str, float]] = None,
                                        use_real_data: bool = False) -> TimeseriesInput:
        """
        Generate forecast scenarios based on input or default data
        
        Args:
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            rain_scenario: Custom rain data
            inflow_scenario: Custom inflow data
            tide_scenario: Custom tide data
            use_real_data: Whether to use real data from APIs
            
        Returns:
            TimeseriesInput object with forecast data
        """
        try:
            if use_real_data:
                # Try to get real data from APIs
                logger.info("Attempting to fetch real data from APIs...")
                real_data = await self.real_data_service.get_real_timeseries_data(start_date, end_date)
                
                # Use real data if available, fallback to synthetic
                tide_data = real_data.get("tide", {})
                inflow_dt_data = real_data.get("inflow_dautieng", {})
                inflow_ta_data = real_data.get("inflow_trian", {})
                
                # If no real data, use synthetic
                if not tide_data:
                    logger.warning("No real tide data available, using synthetic data")
                    tide_data = self.timeseries_utils.generate_tide_scenario(start_date, end_date, tide_scenario)
                else:
                    logger.info(f"Using real tide data: {len(tide_data)} points")
                
                if not inflow_dt_data:
                    logger.warning("No real Hồ Dầu Tiếng data available, using synthetic data")
                    inflow_dt_data = self.timeseries_utils.generate_inflow_scenario(start_date, end_date, inflow_scenario, 24.0)
                else:
                    logger.info(f"Using real Hồ Dầu Tiếng data: {len(inflow_dt_data)} points")
                
                if not inflow_ta_data:
                    logger.warning("No real Hồ Trị An data available, using synthetic data")
                    inflow_ta_data = self.timeseries_utils.generate_inflow_scenario(start_date, end_date, inflow_scenario, 800.0)
                else:
                    logger.info(f"Using real Hồ Trị An data: {len(inflow_ta_data)} points")
                
                # Always use synthetic rain data (no real rain API available)
                rain_data = self.timeseries_utils.generate_rain_scenario(start_date, end_date, rain_scenario)
                
                return TimeseriesInput(
                    rain=rain_data,
                    tide=tide_data,
                    inflow_dautieng=inflow_dt_data,
                    inflow_trian=inflow_ta_data
                )
            else:
                # Generate synthetic data
                logger.info("Using synthetic data for simulation")
                rain_data = self.timeseries_utils.generate_rain_scenario(start_date, end_date, rain_scenario)
                tide_data = self.timeseries_utils.generate_tide_scenario(start_date, end_date, tide_scenario)
                inflow_dt_data = self.timeseries_utils.generate_inflow_scenario(start_date, end_date, inflow_scenario, 24.0)
                inflow_ta_data = self.timeseries_utils.generate_inflow_scenario(start_date, end_date, inflow_scenario, 800.0)
                
                return TimeseriesInput(
                    rain=rain_data,
                    tide=tide_data,
                    inflow_dautieng=inflow_dt_data,
                    inflow_trian=inflow_ta_data
                )
                
        except Exception as e:
            logger.error(f"Error generating forecast scenarios: {str(e)}")
            raise