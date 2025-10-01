"""
Node service for SWMM Service v2
Extracted from main_old.py
"""

import re
import logging
from typing import Dict, List, Any
from ..utils.swmm_utils import get_node_detailed_info
from ..config.settings import settings

logger = logging.getLogger(__name__)


def get_available_nodes() -> Dict[str, Any]:
    """
    Get list of all available nodes with coordinates (from main_old.py)
    
    Returns:
        Dictionary with success status and node data
    """
    try:
        # Đọc danh sách nodes từ model.inp
        with open(settings.get_inp_file_path(), "r", encoding='utf-8') as f:
            content = f.read()
        
        # Đọc tọa độ từ phần COORDINATES
        coordinates = {}
        coords_pattern = r'\[COORDINATES\](.*?)(?=\[|\Z)'
        coords_match = re.search(coords_pattern, content, re.DOTALL)
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
        
        logger.info(f"Loaded {len(coordinates)} coordinates from INP file")
        
        nodes = []
        
        # Tìm trong [JUNCTIONS]
        junctions_pattern = r'\[JUNCTIONS\](.*?)(?=\[|\Z)'
        junctions_match = re.search(junctions_pattern, content, re.DOTALL)
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
                        
                        # Sử dụng tọa độ thực từ file INP nếu có
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
                        # Nếu không parse được tọa độ, dùng giá trị mặc định
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
        
        # Tìm trong [STORAGE]
        storage_pattern = r'\[STORAGE\](.*?)(?=\[|\Z)'
        storage_match = re.search(storage_pattern, content, re.DOTALL)
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
                        
                        # Sử dụng tọa độ thực từ file INP nếu có
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
                        # Sử dụng tọa độ thực từ file INP nếu có
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
