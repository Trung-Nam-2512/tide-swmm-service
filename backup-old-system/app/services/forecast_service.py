"""
Forecast service for SWMM service
"""

import logging
from typing import List, Dict, Any, Optional
from ..schemas.forecast import WaterLevelForecast, ForecastLevel, NodeInfo
from ..schemas.timeseries import TimeseriesInput
from ..utils.flood_risk_utils import FloodRiskUtils
from ..utils.node_utils import NodeUtils
from .swmm_service import SWMMService
from .timeseries_service import TimeseriesService

logger = logging.getLogger(__name__)


class ForecastService:
    """Service for water level forecasting"""
    
    def __init__(self):
        self.swmm_service = SWMMService()
        self.timeseries_service = TimeseriesService()
        self.flood_risk_utils = FloodRiskUtils()
        self.node_utils = NodeUtils()
    
    def create_water_level_forecast(self, 
                                   node_id: str, 
                                   simulation_results: List[Dict[str, Any]], 
                                   inp_content: str,
                                   current_time: Optional[str] = None) -> WaterLevelForecast:
        """
        Create water level forecast for a specific node
        
        Args:
            node_id: Node ID to forecast
            simulation_results: Results from SWMM simulation
            inp_content: INP file content for node info
            current_time: Current time (optional)
            
        Returns:
            WaterLevelForecast object
        """
        try:
            # Find node in simulation results (matching main_old.py format)
            node_data = None
            for result in simulation_results:
                if result["node"] == node_id:
                    node_data = result
                    break
            
            if not node_data:
                raise ValueError(f"Node {node_id} not found in simulation results")
            
            time_series = node_data["time_series"]
            if not time_series:
                raise ValueError(f"No time series data for node {node_id}")
            
            # Get detailed node information
            node_info = self.node_utils.get_node_detailed_info(node_id, inp_content)
            
            # Get current water level (last time step)
            current_depth = time_series[-1]["depth"] if time_series else 0.0
            current_level = current_depth + node_info.invert_elevation
            
            # Create forecast levels
            forecast_levels = []
            for ts in time_series:
                water_level = ts["depth"] + node_info.invert_elevation
                forecast_levels.append(ForecastLevel(
                    time=ts["time"],
                    level=water_level
                ))
            
            # Get maximum forecast level
            max_depth = node_data["max_depth_m"]
            max_forecast_level = max_depth + node_info.invert_elevation
            
            # Calculate flood risk
            flood_risk, flood_probability = self.flood_risk_utils.calculate_flood_risk(
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
            
        except Exception as e:
            logger.error(f"Error creating water level forecast for {node_id}: {str(e)}")
            raise
    
    async def generate_forecast_scenarios(self, 
                                        start_date: str, 
                                        end_date: str, 
                                        rain_scenario: Optional[Dict[str, float]] = None,
                                        inflow_scenario: Optional[Dict[str, float]] = None,
                                        tide_scenario: Optional[Dict[str, float]] = None,
                                        use_real_data: bool = False) -> TimeseriesInput:
        """
        Generate forecast scenarios
        
        Args:
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            rain_scenario: Custom rain data
            inflow_scenario: Custom inflow data
            tide_scenario: Custom tide data
            
        Returns:
            TimeseriesInput object
        """
        return await self.timeseries_service.generate_forecast_scenarios(
            start_date, end_date, rain_scenario, inflow_scenario, tide_scenario, use_real_data
        )
    
    def run_forecast_simulation(self, 
                               timeseries: TimeseriesInput, 
                               inp_content: str) -> List[Dict[str, Any]]:
        """
        Run forecast simulation
        
        Args:
            timeseries: TimeseriesInput object
            inp_content: INP file content
            
        Returns:
            List of simulation results
        """
        try:
            # Write INP file
            self.swmm_service.write_inp_file(timeseries)
            
            # Run simulation
            return self.swmm_service.run_simulation()
            
        except Exception as e:
            logger.error(f"Error running forecast simulation: {str(e)}")
            raise
