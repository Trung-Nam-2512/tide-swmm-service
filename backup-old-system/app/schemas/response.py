"""
Response schemas for SWMM service
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response schema"""
    status: str
    service: str
    version: str


class WaterLevelResponse(BaseModel):
    """Water level forecast response schema"""
    success: bool
    data: List[Dict[str, Any]]
    count: int
    simulation_info: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class NodeListResponse(BaseModel):
    """Node list response schema"""
    success: bool
    data: List[Dict[str, Any]]
    count: int
    message: Optional[str] = None
