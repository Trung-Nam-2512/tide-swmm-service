"""
Node utilities for SWMM service
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from ..schemas.forecast import NodeInfo

logger = logging.getLogger(__name__)


class NodeUtils:
    """Utility class for node operations"""
    
    @staticmethod
    def get_node_detailed_info(node_id: str, inp_content: str) -> NodeInfo:
        """
        Get detailed information of a node from INP file content
        
        Args:
            node_id: Node ID to get info for
            inp_content: Content of INP file
            
        Returns:
            NodeInfo object with node details
        """
        try:
            # Determine node type
            node_type = "JUNCTION"
            if "SG" in node_id:
                node_type = "STORAGE"
            elif "OUT" in node_id or "OUTFALL" in node_id:
                node_type = "OUTFALL"
            
            # Get coordinates
            x_coord, y_coord = NodeUtils._get_node_coordinates(node_id, inp_content)
            
            # Get node parameters based on type
            if node_type == "JUNCTION":
                invert_elevation, max_depth, initial_depth, surface_depth, ponded_area = NodeUtils._get_junction_info(node_id, inp_content)
            elif node_type == "STORAGE":
                invert_elevation, max_depth, initial_depth, surface_depth, ponded_area = NodeUtils._get_storage_info(node_id, inp_content)
            else:
                # Default values for other node types
                invert_elevation, max_depth, initial_depth, surface_depth, ponded_area = 0.0, 0.0, 0.0, 0.0, 0.0
            
            # Calculate ground elevation
            ground_elevation = invert_elevation + max_depth
            
            return NodeInfo(
                node_id=node_id,
                node_type=node_type,
                x_coordinate=x_coord,
                y_coordinate=y_coord,
                invert_elevation=invert_elevation,
                ground_elevation=ground_elevation,
                max_depth=max_depth,
                initial_depth=initial_depth,
                surface_depth=surface_depth,
                ponded_area=ponded_area
            )
            
        except Exception as e:
            logger.warning(f"Could not read detailed info for {node_id}: {str(e)}")
            return NodeUtils._get_default_node_info(node_id)
    
    @staticmethod
    def _get_node_coordinates(node_id: str, inp_content: str) -> Tuple[float, float]:
        """Get node coordinates from COORDINATES section"""
        try:
            coords_pattern = r'\[COORDINATES\](.*?)(?=\[|\Z)'
            coords_match = re.search(coords_pattern, inp_content, re.DOTALL)
            
            if coords_match:
                coords_content = coords_match.group(1)
                coord_pattern = rf'^{re.escape(node_id)}\s+([0-9.-]+)\s+([0-9.-]+)'
                coord_match = re.search(coord_pattern, coords_content, re.MULTILINE)
                
                if coord_match:
                    return float(coord_match.group(1)), float(coord_match.group(2))
            
            return 0.0, 0.0
            
        except Exception as e:
            logger.error(f"Error getting coordinates for {node_id}: {str(e)}")
            return 0.0, 0.0
    
    @staticmethod
    def _get_junction_info(node_id: str, inp_content: str) -> Tuple[float, float, float, float, float]:
        """Get junction information from JUNCTIONS section"""
        try:
            section_pattern = r'\[JUNCTIONS\](.*?)(?=\[|\Z)'
            section_match = re.search(section_pattern, inp_content, re.DOTALL)
            
            if section_match:
                section_content = section_match.group(1)
                # Format: Name Elevation MaxDepth InitDepth SurDepth Aponded
                node_pattern = rf'^{re.escape(node_id)}\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)'
                node_match = re.search(node_pattern, section_content, re.MULTILINE)
                
                if node_match:
                    return (
                        float(node_match.group(1)),  # invert_elevation
                        float(node_match.group(2)),  # max_depth
                        float(node_match.group(3)),  # initial_depth
                        float(node_match.group(4)),  # surface_depth
                        float(node_match.group(5))   # ponded_area
                    )
            
            return 0.0, 0.0, 0.0, 0.0, 0.0
            
        except Exception as e:
            logger.error(f"Error getting junction info for {node_id}: {str(e)}")
            return 0.0, 0.0, 0.0, 0.0, 0.0
    
    @staticmethod
    def _get_storage_info(node_id: str, inp_content: str) -> Tuple[float, float, float, float, float]:
        """Get storage information from STORAGE section"""
        try:
            section_pattern = r'\[STORAGE\](.*?)(?=\[|\Z)'
            section_match = re.search(section_pattern, inp_content, re.DOTALL)
            
            if section_match:
                section_content = section_match.group(1)
                # Format: Name Elevation MaxDepth InitDepth SurDepth Aponded
                node_pattern = rf'^{re.escape(node_id)}\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)'
                node_match = re.search(node_pattern, section_content, re.MULTILINE)
                
                if node_match:
                    return (
                        float(node_match.group(1)),  # invert_elevation
                        float(node_match.group(2)),  # max_depth
                        float(node_match.group(3)),  # initial_depth
                        float(node_match.group(4)),  # surface_depth
                        float(node_match.group(5))   # ponded_area
                    )
            
            return 0.0, 0.0, 0.0, 0.0, 0.0
            
        except Exception as e:
            logger.error(f"Error getting storage info for {node_id}: {str(e)}")
            return 0.0, 0.0, 0.0, 0.0, 0.0
    
    @staticmethod
    def _get_default_node_info(node_id: str) -> NodeInfo:
        """Get default node information when parsing fails"""
        if "DN" in node_id:
            return NodeInfo(
                node_id=node_id,
                node_type="JUNCTION",
                x_coordinate=0.0,
                y_coordinate=0.0,
                invert_elevation=0.0,
                ground_elevation=2.0,
                max_depth=20.0,
                initial_depth=0.0,
                surface_depth=0.0,
                ponded_area=0.0
            )
        elif "SG" in node_id:
            return NodeInfo(
                node_id=node_id,
                node_type="STORAGE",
                x_coordinate=0.0,
                y_coordinate=0.0,
                invert_elevation=0.0,
                ground_elevation=3.0,
                max_depth=30.0,
                initial_depth=0.0,
                surface_depth=0.0,
                ponded_area=0.0
            )
        else:
            return NodeInfo(
                node_id=node_id,
                node_type="JUNCTION",
                x_coordinate=0.0,
                y_coordinate=0.0,
                invert_elevation=0.0,
                ground_elevation=2.5,
                max_depth=25.0,
                initial_depth=0.0,
                surface_depth=0.0,
                ponded_area=0.0
            )
    
    @staticmethod
    def get_available_nodes(inp_content: str) -> List[Dict[str, any]]:
        """
        Get list of all available nodes from INP file content
        
        Args:
            inp_content: Content of INP file
            
        Returns:
            List of node dictionaries
        """
        try:
            nodes = []
            
            # Get coordinates first
            coordinates = NodeUtils._extract_coordinates(inp_content)
            
            # Get junctions
            nodes.extend(NodeUtils._extract_junctions(inp_content, coordinates))
            
            # Get storage nodes
            nodes.extend(NodeUtils._extract_storage_nodes(inp_content, coordinates))
            
            return nodes
            
        except Exception as e:
            logger.error(f"Error getting available nodes: {str(e)}")
            return []
    
    @staticmethod
    def _extract_coordinates(inp_content: str) -> Dict[str, Tuple[float, float]]:
        """Extract coordinates from COORDINATES section"""
        coordinates = {}
        
        try:
            coords_pattern = r'\[COORDINATES\](.*?)(?=\[|\Z)'
            coords_match = re.search(coords_pattern, inp_content, re.DOTALL)
            
            if coords_match:
                coords_content = coords_match.group(1)
                coord_pattern = r'^([A-Za-z0-9_]+)\s+([0-9.-]+)\s+([0-9.-]+)'
                
                for match in re.finditer(coord_pattern, coords_content, re.MULTILINE):
                    node_id = match.group(1)
                    if not node_id.startswith(';;'):
                        try:
                            x_coord = float(match.group(2))
                            y_coord = float(match.group(3))
                            coordinates[node_id] = (x_coord, y_coord)
                        except (ValueError, IndexError):
                            pass
        except Exception as e:
            logger.error(f"Error extracting coordinates: {str(e)}")
        
        return coordinates
    
    @staticmethod
    def _extract_junctions(inp_content: str, coordinates: Dict[str, Tuple[float, float]]) -> List[Dict[str, any]]:
        """Extract junction nodes from JUNCTIONS section"""
        nodes = []
        
        try:
            junctions_pattern = r'\[JUNCTIONS\](.*?)(?=\[|\Z)'
            junctions_match = re.search(junctions_pattern, inp_content, re.DOTALL)
            
            if junctions_match:
                junctions_content = junctions_match.group(1)
                node_pattern = r'^([A-Za-z0-9_]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)'
                
                for match in re.finditer(node_pattern, junctions_content, re.MULTILINE):
                    node_id = match.group(1)
                    if not node_id.startswith(';;'):
                        try:
                            invert_elevation = float(match.group(2))
                            max_depth = float(match.group(3))
                            initial_depth = float(match.group(4))
                            ground_elevation = invert_elevation + max_depth
                            
                            x_coord, y_coord = coordinates.get(node_id, (106.7009, 10.7769))
                            
                            nodes.append({
                                "node_id": node_id,
                                "node_type": "JUNCTION",
                                "x_coordinate": x_coord,
                                "y_coordinate": y_coord,
                                "invert_elevation": invert_elevation,
                                "ground_elevation": ground_elevation,
                                "max_depth": max_depth,
                                "initial_depth": initial_depth
                            })
                        except (ValueError, IndexError):
                            # Use default values if parsing fails
                            x_coord, y_coord = coordinates.get(node_id, (106.7009, 10.7769))
                            nodes.append({
                                "node_id": node_id,
                                "node_type": "JUNCTION",
                                "x_coordinate": x_coord,
                                "y_coordinate": y_coord,
                                "invert_elevation": -2.0,
                                "ground_elevation": 5.0,
                                "max_depth": 7.0,
                                "initial_depth": 0.0
                            })
        except Exception as e:
            logger.error(f"Error extracting junctions: {str(e)}")
        
        return nodes
    
    @staticmethod
    def _extract_storage_nodes(inp_content: str, coordinates: Dict[str, Tuple[float, float]]) -> List[Dict[str, any]]:
        """Extract storage nodes from STORAGE section"""
        nodes = []
        
        try:
            storage_pattern = r'\[STORAGE\](.*?)(?=\[|\Z)'
            storage_match = re.search(storage_pattern, inp_content, re.DOTALL)
            
            if storage_match:
                storage_content = storage_match.group(1)
                node_pattern = r'^([A-Za-z0-9_]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)'
                
                for match in re.finditer(node_pattern, storage_content, re.MULTILINE):
                    node_id = match.group(1)
                    if not node_id.startswith(';;'):
                        try:
                            invert_elevation = float(match.group(2))
                            max_depth = float(match.group(3))
                            initial_depth = float(match.group(4))
                            ground_elevation = invert_elevation + max_depth
                            
                            x_coord, y_coord = coordinates.get(node_id, (106.7009, 10.7769))
                            
                            nodes.append({
                                "node_id": node_id,
                                "node_type": "STORAGE",
                                "x_coordinate": x_coord,
                                "y_coordinate": y_coord,
                                "invert_elevation": invert_elevation,
                                "ground_elevation": ground_elevation,
                                "max_depth": max_depth,
                                "initial_depth": initial_depth
                            })
                        except (ValueError, IndexError):
                            # Use default values if parsing fails
                            x_coord, y_coord = coordinates.get(node_id, (106.7009, 10.7769))
                            nodes.append({
                                "node_id": node_id,
                                "node_type": "STORAGE",
                                "x_coordinate": x_coord,
                                "y_coordinate": y_coord,
                                "invert_elevation": -2.0,
                                "ground_elevation": 5.0,
                                "max_depth": 7.0,
                                "initial_depth": 0.0
                            })
        except Exception as e:
            logger.error(f"Error extracting storage nodes: {str(e)}")
        
        return nodes
