"""
Forecast routes for water level forecast endpoints
"""

from fastapi import APIRouter, Body, Query
from typing import Optional
from ..controllers.forecast_controller import ForecastController
from ..schemas.forecast import ForecastRequest

# Create router
forecast_router = APIRouter(prefix="/swmm-api", tags=["Water Level Forecast"])

# Initialize controller
forecast_controller = ForecastController()


@forecast_router.post("/forecast-water-levels")
async def forecast_water_levels(request: ForecastRequest = Body(...)):
    """
    Forecast water levels for all nodes or selected nodes
    
    Args:
        request: ForecastRequest object with forecast parameters
        
    Returns:
        Dictionary with forecast results
    """
    return await forecast_controller.forecast_water_levels(request)


@forecast_router.get("/forecast-water-level/{node_id}")
def get_node_forecast(
    node_id: str, 
    start_date: str = Query(..., description="Start date (MM/DD/YYYY)"),
    end_date: str = Query(..., description="End date (MM/DD/YYYY)")
):
    """
    Get water level forecast for a specific node
    
    Args:
        node_id: Node ID to forecast
        start_date: Start date in MM/DD/YYYY format
        end_date: End date in MM/DD/YYYY format
        
    Returns:
        Dictionary with node forecast
    """
    return forecast_controller.get_node_forecast(node_id, start_date, end_date)


@forecast_router.get("/water-level-forecast")
async def get_water_level_forecast(
    start_date: str = Query(..., description="Start date (MM/DD/YYYY)"),
    end_date: str = Query(..., description="End date (MM/DD/YYYY)"),
    nodes_filter: Optional[str] = Query(None, description="Comma-separated list of node IDs to filter"),
    use_cached: bool = Query(False, description="Use cached results if available"),
    force_run: bool = Query(False, description="Force run simulation even if cache exists")
):
    """
    Get water level forecast using cached results or run new simulation
    
    Args:
        start_date: Start date in MM/DD/YYYY format
        end_date: End date in MM/DD/YYYY format
        nodes_filter: Comma-separated list of node IDs to filter
        use_cached: Use cached results if available
        force_run: Force run simulation even if cache exists
        
    Returns:
        Dictionary with water level forecast results
    """
    return await forecast_controller.forecast_water_levels(
        start_date, end_date, nodes_filter, use_cached, force_run
    )


@forecast_router.get("/water-level-forecast-real")
async def get_water_level_forecast_with_real_data(
    start_date: str = Query(..., description="Start date (MM/DD/YYYY)"),
    end_date: str = Query(..., description="End date (MM/DD/YYYY)"),
    nodes_filter: Optional[str] = Query(None, description="Comma-separated list of node IDs to filter"),
    use_cached: bool = Query(False, description="Use cached results if available"),
    force_run: bool = Query(False, description="Force run simulation even if cache exists")
):
    """
    Get water level forecast using REAL DATA from APIs
    
    Args:
        start_date: Start date in MM/DD/YYYY format
        end_date: End date in MM/DD/YYYY format
        nodes_filter: Comma-separated list of node IDs to filter
        use_cached: Use cached results if available
        force_run: Force run simulation even if cache exists
        
    Returns:
        Dictionary with water level forecast results using real data
    """
    return await forecast_controller.get_water_level_forecast_with_real_data(
        start_date, end_date, nodes_filter, use_cached, force_run
    )
