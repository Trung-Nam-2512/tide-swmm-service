"""
Main application file for SWMM service
Refactored with clean architecture
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config.settings import Settings
from .routes import swmm_router, forecast_router, node_router, health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "message": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs": "/docs"
    }

# Include routers
app.include_router(swmm_router)
app.include_router(forecast_router)
app.include_router(node_router)
app.include_router(health_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.HOST, 
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
