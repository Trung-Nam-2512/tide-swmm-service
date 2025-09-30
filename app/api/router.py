"""
Main API router
"""

from fastapi import APIRouter
from .endpoints import swmm, data

api_router = APIRouter()

# Include các endpoint routers
api_router.include_router(swmm.router, prefix="/swmm", tags=["SWMM Simulation"])
api_router.include_router(data.router, prefix="/data", tags=["Data Management"])