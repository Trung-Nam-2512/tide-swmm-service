"""
Node controller for handling node-related requests
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from ..services.node_service import NodeService
from ..services.forecast_service import ForecastService

logger = logging.getLogger(__name__)


class NodeController:
    """Controller for node operations"""
    
    def __init__(self):
        self.node_service = NodeService()
        self.forecast_service = ForecastService()
    
    def get_available_nodes(self) -> Dict[str, Any]:
        """
        Get list of all available nodes
        
        Returns:
            Dictionary with node list
        """
        return self.node_service.get_available_nodes()
    
    def get_node_info(self, node_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific node
        
        Args:
            node_id: Node ID to get info for
            
        Returns:
            Dictionary with node information
        """
        try:
            return self.node_service.get_node_info(node_id)
        except Exception as e:
            logger.error(f"Failed to get node info for {node_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get node info: {str(e)}")
    
    def get_flood_risk_summary(self, 
                              start_date: str, 
                              end_date: str) -> Dict[str, Any]:
        """
        Get flood risk summary for all nodes
        
        Args:
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            
        Returns:
            Dictionary with flood risk summary
        """
        try:
            # Generate forecast scenarios
            timeseries = self.forecast_service.generate_forecast_scenarios(start_date, end_date)
            
            # Read INP file content
            from ..config.settings import Settings
            settings = Settings()
            
            with open(settings.get_inp_file_path(), "r") as f:
                inp_content = f.read()
            
            # Run simulation
            simulation_results = self.forecast_service.run_forecast_simulation(timeseries, inp_content)
            
            # Get flood risk summary
            summary = self.node_service.get_flood_risk_summary(simulation_results, inp_content)
            
            # Add forecast period info
            summary["forecast_period"] = {
                "start_date": start_date,
                "end_date": end_date
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Flood risk summary failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Flood risk summary failed: {str(e)}")
        finally:
            # Cleanup temporary files
            from ..utils.file_utils import FileUtils
            file_utils = FileUtils()
            file_utils.cleanup_temp_files([
                "temp_model.inp", 
                "temp_model.rpt", 
                "temp_model.out"
            ])
