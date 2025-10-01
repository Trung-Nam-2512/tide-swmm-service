"""
Flood risk calculation utilities for SWMM service
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class FloodRiskUtils:
    """Utility class for flood risk calculations"""
    
    @staticmethod
    def calculate_flood_risk(max_depth: float, 
                           invert_elevation: float = 0.0, 
                           ground_elevation: float = 0.0, 
                           node_capacity: float = 25.0) -> Tuple[str, float]:
        """
        Calculate flood risk based on water level
        
        Args:
            max_depth: Maximum water depth in meters
            invert_elevation: Invert elevation in meters
            ground_elevation: Ground elevation in meters
            node_capacity: Node capacity in meters
            
        Returns:
            Tuple of (risk_level, probability)
        """
        try:
            # Calculate actual water level (water level = depth + invert elevation)
            water_level = max_depth + invert_elevation
            
            # Calculate flood ratio
            if ground_elevation > invert_elevation and (ground_elevation - invert_elevation) > 0:
                # Use actual ground elevation
                flood_ratio = max_depth / (ground_elevation - invert_elevation)
            elif node_capacity > 0:
                # Fallback to node capacity
                flood_ratio = max_depth / node_capacity
            else:
                # Fallback to max_depth if all else fails
                flood_ratio = min(max_depth / 25.0, 1.0)  # Assume 25m as default capacity
            
            # Ensure flood_ratio is within reasonable range
            flood_ratio = max(0.0, min(flood_ratio, 2.0))  # Cap at 200%
            
            # Evaluate risk based on flood ratio
            if flood_ratio <= 0.3:
                return "LOW", 0.1
            elif flood_ratio <= 0.6:
                return "MEDIUM", 0.3
            elif flood_ratio <= 0.85:
                return "HIGH", 0.7
            else:
                return "CRITICAL", 0.9
                
        except Exception as e:
            logger.error(f"Error calculating flood risk: {str(e)}")
            return "LOW", 0.1
    
    @staticmethod
    def calculate_flood_risk_by_water_level(water_level: float, 
                                          ground_elevation: float,
                                          flood_threshold: float = 0.3) -> Tuple[str, float]:
        """
        Calculate flood risk based on water level vs ground elevation
        
        Args:
            water_level: Current water level in meters
            ground_elevation: Ground elevation in meters
            flood_threshold: Flood threshold in meters above ground
            
        Returns:
            Tuple of (risk_level, probability)
        """
        try:
            # Calculate flood depth relative to ground
            flood_depth = max(0, water_level - ground_elevation)
            
            # Calculate flood probability based on depth
            if flood_depth <= 0:
                return "NONE", 0.0
            elif flood_depth < flood_threshold:
                return "LOW", flood_depth / flood_threshold * 0.3  # max 30%
            elif flood_depth < flood_threshold * 2:
                return "MEDIUM", 0.3 + (flood_depth - flood_threshold) / flood_threshold * 0.3  # 30-60%
            elif flood_depth < flood_threshold * 3:
                return "HIGH", 0.6 + (flood_depth - flood_threshold * 2) / flood_threshold * 0.25  # 60-85%
            else:
                return "CRITICAL", min(0.85 + (flood_depth - flood_threshold * 3) / flood_threshold * 0.15, 1.0)  # 85-100%
                
        except Exception as e:
            logger.error(f"Error calculating flood risk by water level: {str(e)}")
            return "LOW", 0.1
