"""
Node service for SWMM service
"""

import logging
from typing import List, Dict, Any, Optional
from ..utils.node_utils import NodeUtils
from ..utils.file_utils import FileUtils
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class NodeService:
    """Service for node operations"""
    
    def __init__(self):
        self.node_utils = NodeUtils()
        self.file_utils = FileUtils()
        self.settings = Settings()
    
    def get_available_nodes(self) -> Dict[str, Any]:
        """
        Get list of all available nodes with coordinates
        
        Returns:
            Dictionary with success status and node data
        """
        try:
            # Read INP file content
            inp_file_path = self.settings.get_inp_file_path()
            logger.info(f"Reading INP file from: {inp_file_path}")
            with open(inp_file_path, "r", encoding='utf-8') as f:
                inp_content = f.read()
            
            # Get nodes from INP content
            nodes = self.node_utils.get_available_nodes(inp_content)
            
            return {
                "success": True,
                "data": nodes,
                "count": len(nodes)
            }
            
        except Exception as e:
            logger.error(f"Failed to get available nodes: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to get available nodes: {str(e)}",
                "data": []
            }
    
    def get_node_info(self, node_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific node
        
        Args:
            node_id: Node ID to get info for
            
        Returns:
            Dictionary with node information
        """
        try:
            # Read INP file content
            with open(self.settings.get_inp_file_path(), "r") as f:
                inp_content = f.read()
            
            # Get node detailed info
            node_info = self.node_utils.get_node_detailed_info(node_id, inp_content)
            
            return {
                "node_id": node_info.node_id,
                "node_type": node_info.node_type,
                "coordinates": {
                    "x": node_info.x_coordinate,
                    "y": node_info.y_coordinate
                },
                "elevation": {
                    "invert_elevation": node_info.invert_elevation,
                    "ground_elevation": node_info.ground_elevation,
                    "max_depth": node_info.max_depth
                },
                "initial_conditions": {
                    "initial_depth": node_info.initial_depth,
                    "surface_depth": node_info.surface_depth,
                    "ponded_area": node_info.ponded_area
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get node info for {node_id}: {str(e)}")
            raise
    
    def get_flood_risk_summary(self, 
                              simulation_results: List[Dict[str, Any]], 
                              inp_content: str) -> Dict[str, Any]:
        """
        Get flood risk summary for all nodes
        
        Args:
            simulation_results: Results from SWMM simulation
            inp_content: INP file content
            
        Returns:
            Dictionary with flood risk summary
        """
        try:
            from ..utils.flood_risk_utils import FloodRiskUtils
            
            flood_risk_utils = FloodRiskUtils()
            
            # Categorize nodes by flood risk
            risk_categories = {
                "LOW": [],
                "MEDIUM": [],
                "HIGH": [],
                "CRITICAL": []
            }
            
            for result in simulation_results:
                # Get node detailed info
                node_info = self.node_utils.get_node_detailed_info(result["node"], inp_content)
                
                # Calculate flood risk
                flood_risk, flood_probability = flood_risk_utils.calculate_flood_risk(
                    result["max_depth_m"], 
                    node_info.invert_elevation, 
                    node_info.ground_elevation, 
                    node_info.max_depth
                )
                
                risk_categories[flood_risk].append({
                    "node_id": result["node"],
                    "node_type": node_info.node_type,
                    "coordinates": {
                        "x": node_info.x_coordinate,
                        "y": node_info.y_coordinate
                    },
                    "max_depth": result["max_depth_m"],
                    "max_water_level": result["max_depth_m"] + node_info.invert_elevation,
                    "flood_probability": flood_probability,
                    "invert_elevation": node_info.invert_elevation,
                    "ground_elevation": node_info.ground_elevation
                })
            
            # Calculate summary
            total_nodes = len(simulation_results)
            summary = {
                "total_nodes": total_nodes,
                "risk_distribution": {
                    "LOW": len(risk_categories["LOW"]),
                    "MEDIUM": len(risk_categories["MEDIUM"]),
                    "HIGH": len(risk_categories["HIGH"]),
                    "CRITICAL": len(risk_categories["CRITICAL"])
                },
                "risk_categories": risk_categories
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get flood risk summary: {str(e)}")
            raise
