"""
Math utilities for SWMM Service v2
Extracted from main_old.py
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def calculate_flood_risk(max_depth: float, 
                        invert_elevation: float = 0.0, 
                        ground_elevation: float = 0.0, 
                        node_capacity: float = 25.0) -> Tuple[str, float]:
    """
    Calculate flood risk based on water level (from main_old.py)
    
    Args:
        max_depth: Maximum water depth in meters
        invert_elevation: Invert elevation in meters
        ground_elevation: Ground elevation in meters
        node_capacity: Node capacity in meters
        
    Returns:
        Tuple of (risk_level, probability)
    """
    # Tính mực nước thực tế (water level = depth + invert elevation)
    water_level = max_depth + invert_elevation
    
    # Tính tỷ lệ ngập lụt
    if ground_elevation > invert_elevation and (ground_elevation - invert_elevation) > 0:
        # Sử dụng cao độ thực tế
        flood_ratio = max_depth / (ground_elevation - invert_elevation)
    elif node_capacity > 0:
        # Fallback to node capacity
        flood_ratio = max_depth / node_capacity
    else:
        # Fallback to max_depth if all else fails
        flood_ratio = min(max_depth / 25.0, 1.0)  # Assume 25m as default capacity
    
    # Đảm bảo flood_ratio trong khoảng hợp lý
    flood_ratio = max(0.0, min(flood_ratio, 2.0))  # Cap at 200%
    
    # Đánh giá nguy cơ dựa trên tỷ lệ ngập lụt
    if flood_ratio <= 0.3:
        return "LOW", 0.1
    elif flood_ratio <= 0.6:
        return "MEDIUM", 0.3
    elif flood_ratio <= 0.85:
        return "HIGH", 0.7
    else:
        return "CRITICAL", 0.9
