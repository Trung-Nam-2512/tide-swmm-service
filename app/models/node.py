"""
Node data models for SWMM Service v2
Extracted from main_old.py
"""

from pydantic import BaseModel


class NodeInfo(BaseModel):
    """Node information model (from main_old.py)"""
    node_id: str
    node_type: str  # "JUNCTION", "STORAGE", "OUTFALL"
    x_coordinate: float
    y_coordinate: float
    invert_elevation: float  # m
    ground_elevation: float  # m
    max_depth: float  # m
    initial_depth: float  # m
    surface_depth: float  # m
    ponded_area: float  # m²
