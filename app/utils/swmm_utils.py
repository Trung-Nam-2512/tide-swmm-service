"""
SWMM utilities for SWMM Service v2
Extracted from main_old.py
"""

import os
import re
import logging
from typing import Dict, Any, List, Tuple
from ..models.node import NodeInfo

logger = logging.getLogger(__name__)


def get_node_detailed_info(node_id: str, inp_file_path: str) -> NodeInfo:
    """
    Get detailed node information from INP file (from main_old.py)
    
    Args:
        node_id: Node ID to get info for
        inp_file_path: Path to INP file
        
    Returns:
        NodeInfo object
    """
    try:
        # Đọc file model.inp để lấy thông tin chi tiết
        with open(inp_file_path, "r", encoding='utf-8') as f:
            content = f.read()
        
        # Xác định loại node
        node_type = "JUNCTION"
        if "SG" in node_id:
            node_type = "STORAGE"
        elif "OUT" in node_id or "OUTFALL" in node_id:
            node_type = "OUTFALL"
        
        # Tìm tọa độ trong [COORDINATES]
        coords_pattern = r'\[COORDINATES\](.*?)(?=\[|\Z)'
        coords_match = re.search(coords_pattern, content, re.DOTALL)
        x_coord, y_coord = 0.0, 0.0
        
        if coords_match:
            coords_content = coords_match.group(1)
            coord_pattern = rf'^{re.escape(node_id)}\s+([0-9.-]+)\s+([0-9.-]+)'
            coord_match = re.search(coord_pattern, coords_content, re.MULTILINE)
            if coord_match:
                x_coord = float(coord_match.group(1))
                y_coord = float(coord_match.group(2))
        
        # Tìm thông tin cao độ và dung tích
        invert_elevation, max_depth, initial_depth, surface_depth, ponded_area = 0.0, 0.0, 0.0, 0.0, 0.0
        
        if node_type == "JUNCTION":
            section_pattern = r'\[JUNCTIONS\](.*?)(?=\[|\Z)'
            section_match = re.search(section_pattern, content, re.DOTALL)
            if section_match:
                section_content = section_match.group(1)
                # Format: Name Elevation MaxDepth InitDepth SurDepth Aponded
                node_pattern = rf'^{re.escape(node_id)}\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)'
                node_match = re.search(node_pattern, section_content, re.MULTILINE)
                if node_match:
                    invert_elevation = float(node_match.group(1))
                    max_depth = float(node_match.group(2))
                    initial_depth = float(node_match.group(3))
                    surface_depth = float(node_match.group(4))
                    ponded_area = float(node_match.group(5))
        
        elif node_type == "STORAGE":
            section_pattern = r'\[STORAGE\](.*?)(?=\[|\Z)'
            section_match = re.search(section_pattern, content, re.DOTALL)
            if section_match:
                section_content = section_match.group(1)
                # Format: Name Elevation MaxDepth InitDepth SurDepth Aponded
                node_pattern = rf'^{re.escape(node_id)}\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)'
                node_match = re.search(node_pattern, section_content, re.MULTILINE)
                if node_match:
                    invert_elevation = float(node_match.group(1))
                    max_depth = float(node_match.group(2))
                    initial_depth = float(node_match.group(3))
                    surface_depth = float(node_match.group(4))
                    ponded_area = float(node_match.group(5))
        
        # Tính cao độ mặt đất (ground elevation = invert + max_depth)
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
        # Fallback to default values
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


def get_node_elevation_data(node_id: str, inp_file_path: str) -> Tuple[float, float, float]:
    """
    Get node elevation data (backward compatibility from main_old.py)
    
    Args:
        node_id: Node ID
        inp_file_path: Path to INP file
        
    Returns:
        Tuple of (invert_elevation, ground_elevation, max_depth)
    """
    node_info = get_node_detailed_info(node_id, inp_file_path)
    return node_info.invert_elevation, node_info.ground_elevation, node_info.max_depth
