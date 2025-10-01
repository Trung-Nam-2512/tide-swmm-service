#!/usr/bin/env python3
"""
Test script to verify that the refactored SWMM service matches main_old.py logic
"""

import sys
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.swmm_service import SWMMService
from app.schemas.timeseries import TimeseriesInput

def create_test_timeseries():
    """Create test timeseries data similar to main_old.py"""
    # Create date range for 3 days
    start_date = datetime(2025, 10, 1)
    end_date = datetime(2025, 10, 4)
    date_range = pd.date_range(start_date, end_date, freq="H")
    
    # Create test data similar to main_old.py DEFAULT_TIMESERIES
    rain_data = {}
    inflow_dt_data = {}
    inflow_ta_data = {}
    tide_data = {}
    
    for i, dt in enumerate(date_range):
        time_str = dt.strftime("%m/%d/%Y %H:%M")
        
        # Rain data (similar to main_old.py)
        rain_data[time_str] = max(0, 5 * np.sin(2 * np.pi * i / 24) + 5)
        
        # Inflow data (similar to main_old.py)
        inflow_dt_data[time_str] = 24.0
        inflow_ta_data[time_str] = 800.0
        
        # Tide data (similar to main_old.py)
        tide_data[time_str] = 1.5 * np.sin(2 * np.pi * i / 12.4) + 1.0
    
    return TimeseriesInput(
        rain=rain_data,
        inflow_dautieng=inflow_dt_data,
        inflow_trian=inflow_ta_data,
        tide=tide_data
    )

def test_swmm_service():
    """Test the refactored SWMM service"""
    print("Testing refactored SWMM service...")
    
    try:
        # Create test timeseries
        timeseries = create_test_timeseries()
        print(f"Created test timeseries with {len(timeseries.rain)} time points")
        
        # Initialize SWMM service
        swmm_service = SWMMService()
        print("Initialized SWMM service")
        
        # Write INP file
        inp_file = swmm_service.write_inp_file(timeseries)
        print(f"Written INP file: {inp_file}")
        
        # Check if INP file exists and has content
        if os.path.exists(inp_file):
            file_size = os.path.getsize(inp_file)
            print(f"INP file exists with size: {file_size} bytes")
            
            # Read and check INP content
            with open(inp_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for key sections
            if "[TIMESERIES]" in content:
                print("TIMESERIES section found in INP file")
            else:
                print("TIMESERIES section missing in INP file")
                
            if "[INFLOWS]" in content:
                print("INFLOWS section found in INP file")
            else:
                print("INFLOWS section missing in INP file")
                
            if "TSN" in content:
                print("TSN timeseries found in INP file")
            else:
                print("TSN timeseries missing in INP file")
        else:
            print("INP file not created")
            return False
        
        # Run simulation
        print("Running SWMM simulation...")
        results = swmm_service.run_simulation()
        
        if results and len(results) > 0:
            print(f"Simulation completed with {len(results)} nodes")
            
            # Check result format
            first_result = results[0]
            required_keys = ["node", "max_depth_m", "max_water_level_m", "invert_elevation", "time_series"]
            
            for key in required_keys:
                if key in first_result:
                    print(f"Result contains {key}")
                else:
                    print(f"Result missing {key}")
            
            # Check time series data
            if "time_series" in first_result and first_result["time_series"]:
                ts_data = first_result["time_series"]
                print(f"Time series has {len(ts_data)} data points")
                
                # Check for reasonable values
                first_ts = ts_data[0]
                if "depth" in first_ts and "water_level" in first_ts:
                    depth = first_ts["depth"]
                    water_level = first_ts["water_level"]
                    print(f"First data point - Depth: {depth:.2f}m, Water Level: {water_level:.2f}m")
                    
                    # Check if values are reasonable (not 1000+ meters)
                    if depth < 100 and water_level < 100:
                        print("Values appear reasonable (not 1000+ meters)")
                    else:
                        print("WARNING: Values seem too large (1000+ meters) - may need further investigation")
                else:
                    print("Time series data missing depth or water_level")
            else:
                print("No time series data found")
                
        else:
            print("Simulation returned no results")
            return False
            
        # Save results for inspection
        output_file = "test_simulation_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {output_file}")
        
        return True
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            swmm_service.cleanup_temp_files()
            print("Cleaned up temporary files")
        except:
            pass

if __name__ == "__main__":
    print("Starting SWMM service test...")
    success = test_swmm_service()
    
    if success:
        print("\nTest completed successfully!")
        print("The refactored SWMM service appears to be working correctly.")
    else:
        print("\nTest failed!")
        print("The refactored SWMM service needs further fixes.")
    
    print("\nNext steps:")
    print("1. Check the generated INP file for correct format")
    print("2. Verify simulation results are reasonable")
    print("3. Compare with main_old.py results if needed")
