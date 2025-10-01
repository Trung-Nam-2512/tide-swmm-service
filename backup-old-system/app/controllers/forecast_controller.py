"""
Forecast controller for handling water level prediction requests
"""

import logging
from typing import Dict, Any, Optional
from ..services.forecast_service import ForecastService
from ..services.node_service import NodeService
from ..utils.file_utils import FileUtils
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class ForecastController:
    """Controller for forecast operations"""
    
    def __init__(self):
        self.forecast_service = ForecastService()
        self.node_service = NodeService()
        self.file_utils = FileUtils()
        self.settings = Settings()
        from ..services.swmm_service import SWMMService
        self.swmm_service = SWMMService()
    
    async def forecast_water_levels(self, 
                                   start_date: str,
                                   end_date: str,
                                   nodes_filter: Optional[str] = None,
                                   use_cached: bool = False,
                                   force_run: bool = False) -> Dict[str, Any]:
        """
        Generate water level forecast
        
        Args:
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            nodes_filter: Comma-separated list of node IDs to filter
            use_cached: Whether to use cached results
            force_run: Force run simulation even if cache exists
            
        Returns:
            Forecast results dictionary
        """
        try:
            # Generate timeseries data (synthetic for now)
            timeseries = await self.forecast_service.generate_forecast_scenarios(
                start_date, end_date
            )
            
            # Write INP file
            self.swmm_service.write_inp_file(timeseries)
            
            # Run simulation
            simulation_results = self.swmm_service.run_simulation()
            
            # Process results
            processed_results = simulation_results
            
            # Filter nodes if requested
            if nodes_filter:
                node_ids = [n.strip() for n in nodes_filter.split(',')]
                processed_results = {
                    k: v for k, v in processed_results.items() 
                    if k in node_ids
                }
            
            return {
                "success": True,
                "data": processed_results,
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "nodes_count": len(processed_results)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in forecast_water_levels: {str(e)}")
            raise
    
    async def get_water_level_forecast_with_real_data(self,
                                                     start_date: str,
                                                     end_date: str,
                                                     nodes_filter: Optional[str] = None,
                                                     use_cached: bool = False,
                                                     force_run: bool = False) -> Dict[str, Any]:
        """
        Get water level forecast using REAL DATA from APIs
        
        Args:
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            nodes_filter: Comma-separated list of node IDs to filter
            use_cached: Whether to use cached results
            force_run: Force run simulation even if cache exists
            
        Returns:
            Forecast results dictionary
        """
        try:
            # Generate timeseries data with REAL data
            timeseries = await self.forecast_service.generate_forecast_scenarios(
                start_date=start_date,
                end_date=end_date,
                use_real_data=True
            )
            
            # Write INP file
            self.swmm_service.write_inp_file(timeseries)
            
            # Run simulation
            simulation_results = self.swmm_service.run_simulation()
            
            # Process results
            processed_results = simulation_results
            
            # Filter nodes if requested
            if nodes_filter:
                node_ids = [n.strip() for n in nodes_filter.split(',')]
                processed_results = {
                    k: v for k, v in processed_results.items() 
                    if k in node_ids
                }
            
            return {
                "success": True,
                "data": processed_results,
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "nodes_count": len(processed_results),
                    "using_real_data": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error in get_water_level_forecast_with_real_data: {str(e)}")
            raise
