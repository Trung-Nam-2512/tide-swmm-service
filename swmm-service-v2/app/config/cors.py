"""
CORS configuration for SWMM Service v2
Extracted from main_old.py
"""

from fastapi.middleware.cors import CORSMiddleware
from .settings import settings


def setup_cors_middleware(app):
    """Setup CORS middleware (from main_old.py)"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],  # Cho phép tất cả HTTP methods
        allow_headers=["*"],  # Cho phép tất cả headers
    )
