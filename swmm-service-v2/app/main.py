"""
Main application file for SWMM Service v2
Refactored from main_old.py
"""

import logging
from fastapi import FastAPI
from .config.settings import settings
from .config.cors import setup_cors_middleware
from .api.v1 import swmm, forecast, nodes

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup CORS middleware
setup_cors_middleware(app)

# Include routers
app.include_router(swmm.swmm_router)
app.include_router(forecast.forecast_router)
app.include_router(nodes.nodes_router)

# Root endpoint
@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "message": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs": "/docs"
    }

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": settings.API_TITLE, 
        "version": settings.API_VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.HOST, 
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
