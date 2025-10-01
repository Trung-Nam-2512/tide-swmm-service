"""
Run SWMM Service v2 server
"""

import uvicorn
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    print("Starting SWMM Service v2...")
    print("Server will be available at: http://localhost:1433")
    print("API docs at: http://localhost:1433/docs")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=1433,
        reload=False,
        log_level="info"
    )
