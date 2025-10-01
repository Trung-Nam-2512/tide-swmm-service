"""
Health controller for handling health check requests
"""

import logging
from ..schemas.response import HealthResponse

logger = logging.getLogger(__name__)


class HealthController:
    """Controller for health check operations"""
    
    def __init__(self):
        pass
    
    def health_check(self) -> HealthResponse:
        """
        Perform health check
        
        Returns:
            HealthResponse object
        """
        return HealthResponse(
            status="healthy",
            service="SWMM Water Level Forecast API",
            version="1.0.0"
        )
