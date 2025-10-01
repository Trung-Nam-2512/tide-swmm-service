"""
Health routes for health check endpoints
"""

from fastapi import APIRouter
from ..controllers.health_controller import HealthController

# Create router
health_router = APIRouter(prefix="/swmm-api", tags=["Health"])

# Initialize controller
health_controller = HealthController()


@health_router.get("/health")
def health_check():
    """
    Health check endpoint
    
    Returns:
        HealthResponse object with service status
    """
    return health_controller.health_check()
