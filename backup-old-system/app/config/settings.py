"""
Settings configuration for SWMM service
"""

import os
from typing import List


class Settings:
    """Application settings"""
    
    # API Configuration
    API_TITLE = "Water Level Forecast API"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "API for  water level forecasting and simulation"
    
    # Server Configuration
    HOST = "0.0.0.0"
    PORT = 1433
    
    # CORS Configuration
    CORS_ORIGINS = [
        "http://localhost:3000",  # Frontend development
        "https://tide.nguyentrungnam.com",  # Frontend production
        "https://www.tide.nguyentrungnam.com",
        "http://wlforecast.baonamdts.com/",  # Frontend production with www
        "*"  # Fallback for development
    ]
    
    # File Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    INP_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "model.inp")  # Use original model.inp as base
    TEMP_INP_FILE = os.path.join(os.path.dirname(__file__), "..", "temp_model.inp")
    
    # Cache Configuration
    CACHE_ENABLED = True
    CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "swmm_simulation_cache.json")
    OUTPUT_JSON_FILE = os.path.join(os.path.dirname(__file__), "..", "swmm_output.json")
    
    # Simulation Configuration
    DEFAULT_TIME_STEP = 60  # minutes (1 hour)
    DEFAULT_SIMULATION_DAYS = 7
    
    # Flood Risk Configuration
    FLOOD_THRESHOLD = 0.3  # meters above ground level
    FLOOD_RISK_LEVELS = {
        "NONE": 0.0,
        "LOW": 0.3,
        "MEDIUM": 0.6,
        "HIGH": 0.85,
        "CRITICAL": 1.0
    }
    
    # Logging Configuration
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def get_cors_origins(cls) -> List[str]:
        """Get CORS origins list"""
        return cls.CORS_ORIGINS
    
    @classmethod
    def get_inp_file_path(cls) -> str:
        """Get INP file path"""
        return cls.INP_FILE
    
    @classmethod
    def get_temp_inp_file_path(cls) -> str:
        """Get temporary INP file path"""
        return cls.TEMP_INP_FILE
