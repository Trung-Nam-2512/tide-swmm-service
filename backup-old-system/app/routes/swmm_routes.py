"""
SWMM routes for simulation endpoints
"""

from fastapi import APIRouter, Body
from ..controllers.swmm_controller import SWMMController
from ..schemas.timeseries import TimeseriesInput, SimulationInput

# Create router
swmm_router = APIRouter(prefix="/swmm-api", tags=["SWMM Simulation"])

# Initialize controller
swmm_controller = SWMMController()


@swmm_router.post("/run-swmm")
def run_model(timeseries: TimeseriesInput = Body(...)):
    """
    Run SWMM simulation with timeseries data
    
    Args:
        timeseries: TimeseriesInput object with rain, inflow, and tide data
        
    Returns:
        Dictionary with simulation results
    """
    return swmm_controller.run_swmm_simulation(timeseries)


@swmm_router.post("/run-simulation")
def run_custom_simulation(simulation_input: SimulationInput = Body(...)):
    """
    Run custom simulation with user-defined data
    
    Args:
        simulation_input: SimulationInput object with custom simulation parameters
        
    Returns:
        Dictionary with custom simulation results
    """
    return swmm_controller.run_custom_simulation(simulation_input)
