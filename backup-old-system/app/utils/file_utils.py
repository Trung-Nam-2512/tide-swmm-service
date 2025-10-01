"""
File utilities for SWMM service
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FileUtils:
    """Utility class for file operations"""
    
    @staticmethod
    def ensure_file_exists(file_path: str, fallback_path: Optional[str] = None) -> bool:
        """
        Ensure file exists, copy from fallback if needed
        
        Args:
            file_path: Target file path
            fallback_path: Fallback file path to copy from
            
        Returns:
            True if file exists or was created successfully
        """
        try:
            if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
                return True
                
            if fallback_path and os.path.exists(fallback_path):
                logger.info(f"Copying {fallback_path} to {file_path}")
                with open(fallback_path, 'r') as src, open(file_path, 'w') as dst:
                    dst.write(src.read())
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error ensuring file exists: {str(e)}")
            return False
    
    @staticmethod
    def load_json_cache(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load data from JSON cache file
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Loaded data or None if failed
        """
        try:
            if not os.path.exists(file_path):
                return None
                
            with open(file_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading JSON cache from {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def save_json_cache(data: Dict[str, Any], file_path: str) -> bool:
        """
        Save data to JSON cache file
        
        Args:
            data: Data to save
            file_path: Path to JSON file
            
        Returns:
            True if saved successfully
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
            
        except Exception as e:
            logger.error(f"Error saving JSON cache to {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def cleanup_temp_files(file_paths: list) -> None:
        """
        Clean up temporary files
        
        Args:
            file_paths: List of file paths to remove
        """
        import gc
        import time
        
        gc.collect()
        time.sleep(2)
        
        for file_path in file_paths:
            if os.path.exists(file_path):
                for attempt in range(3):
                    try:
                        os.remove(file_path)
                        break
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(1)
                            gc.collect()
                        else:
                            logger.warning(f"Could not delete {file_path} - file may be in use")
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        Get file size in bytes
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in bytes, 0 if file doesn't exist
        """
        try:
            return os.path.getsize(file_path) if os.path.exists(file_path) else 0
        except Exception as e:
            logger.error(f"Error getting file size for {file_path}: {str(e)}")
            return 0
