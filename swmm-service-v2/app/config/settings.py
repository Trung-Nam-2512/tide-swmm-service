"""
Settings configuration for SWMM Service v2
Extracted from main_old.py
"""

import os
from typing import List


class Settings:
    """Application settings extracted from main_old.py"""
    
    # API Configuration
    API_TITLE = "SWMM Water Level Forecast API"
    API_VERSION = "2.0.0"
    API_DESCRIPTION = "API for water level forecasting and simulation - Refactored from main_old.py"
    
    # Server Configuration
    HOST = "0.0.0.0"
    PORT = 1433
    
    # CORS Configuration (from main_old.py)
    CORS_ORIGINS = [
        "http://localhost:3000",  # Frontend development
        "https://tide.nguyentrungnam.com",  # Frontend production
        "https://www.tide.nguyentrungnam.com",
        "http://wlforecast.baonamdts.com/",  # Frontend production with www
        "*"  # Fallback for development
    ]
    
    # File Paths (from main_old.py)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    INP_FILE = os.path.join(BASE_DIR, "model.inp")
    TEMP_INP_FILE = os.path.join(BASE_DIR, "temp_model.inp")
    
    # Cache Configuration
    CACHE_ENABLED = True
    CACHE_FILE = os.path.join(BASE_DIR, "swmm_simulation_cache.json")
    OUTPUT_JSON_FILE = os.path.join(BASE_DIR, "swmm_output.json")
    
    # Simulation Configuration
    DEFAULT_TIME_STEP = 60  # minutes (1 hour)
    DEFAULT_SIMULATION_DAYS = 7
    
    # Flood Risk Configuration (from main_old.py)
    FLOOD_THRESHOLD = 0.3  # meters above ground level
    FLOOD_RISK_LEVELS = {
        "LOW": 0.1,
        "MEDIUM": 0.3,
        "HIGH": 0.7,
        "CRITICAL": 0.9
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


# Global settings instance
settings = Settings()
