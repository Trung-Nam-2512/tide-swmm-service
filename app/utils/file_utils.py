"""
File utilities for SWMM Service v2
Extracted from main_old.py
"""

import os
import logging
import time
import gc
from typing import List

logger = logging.getLogger(__name__)


def cleanup_temp_files(files_to_remove: List[str]):
    """
    Clean up temporary files (from main_old.py)
    
    Args:
        files_to_remove: List of file paths to remove
    """
    for file_path in files_to_remove:
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


def ensure_file_exists(file_path: str, fallback_path: str = None) -> bool:
    """
    Ensure file exists, copy from fallback if needed
    
    Args:
        file_path: Target file path
        fallback_path: Fallback file path to copy from
        
    Returns:
        True if file exists or was created successfully
    """
    if os.path.exists(file_path):
        return True
    
    if fallback_path and os.path.exists(fallback_path):
        try:
            with open(fallback_path, 'r', encoding='utf-8') as src, \
                 open(file_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            logger.info(f"Copied {fallback_path} to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to copy {fallback_path} to {file_path}: {e}")
            return False
    
    return False
