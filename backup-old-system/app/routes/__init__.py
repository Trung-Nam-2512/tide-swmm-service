"""
Routes module for SWMM service
"""

from .swmm_routes import swmm_router
from .forecast_routes import forecast_router
from .node_routes import node_router
from .health_routes import health_router

__all__ = [
    "swmm_router",
    "forecast_router",
    "node_router",
    "health_router"
]
