"""
Test script for SWMM Service v2
Test the refactored system step by step
"""

import sys
import os
import logging

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from app.config.settings import settings
        print("[OK] Settings imported successfully")
        
        from app.models.timeseries import TimeseriesInput
        print("[OK] Timeseries models imported successfully")
        
        from app.models.forecast import WaterLevelForecast, ForecastLevel
        print("[OK] Forecast models imported successfully")
        
        from app.models.node import NodeInfo
        print("[OK] Node models imported successfully")
        
        from app.services.timeseries_service import interpolate_ts, generate_forecast_scenarios
        print("[OK] Timeseries service imported successfully")
        
        from app.services.node_service import get_available_nodes
        print("[OK] Node service imported successfully")
        
        from app.services.swmm_service import write_inp, run_and_parse_swmm
        print("[OK] SWMM service imported successfully")
        
        from app.services.forecast_service import create_water_level_forecast
        print("[OK] Forecast service imported successfully")
        
        from app.utils.math_utils import calculate_flood_risk
        print("[OK] Math utils imported successfully")
        
        from app.utils.file_utils import cleanup_temp_files
        print("[OK] File utils imported successfully")
        
        from app.utils.swmm_utils import get_node_detailed_info
        print("[OK] SWMM utils imported successfully")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return False

def test_settings():
    """Test settings configuration"""
    print("\nTesting settings...")
    
    try:
        from app.config.settings import settings
        
        print(f"[OK] API Title: {settings.API_TITLE}")
        print(f"[OK] API Version: {settings.API_VERSION}")
        print(f"[OK] INP File: {settings.get_inp_file_path()}")
        print(f"[OK] Temp INP File: {settings.get_temp_inp_file_path()}")
        
        # Check if INP file exists
        if os.path.exists(settings.get_inp_file_path()):
            print("[OK] INP file exists")
        else:
            print("[ERROR] INP file not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"[ERROR] Settings test failed: {e}")
        return False

def test_timeseries_service():
    """Test timeseries service"""
    print("\nTesting timeseries service...")
    
    try:
        from app.services.timeseries_service import interpolate_ts, generate_forecast_scenarios
        
        # Test interpolation
        test_data = {
            "01/01/2024 00:00": 0.0,
            "01/01/2024 12:00": 5.0,
            "01/02/2024 00:00": 0.0
        }
        
        interpolated = interpolate_ts(test_data)
        print(f"[OK] Interpolation test passed: {len(interpolated)} data points")
        
        # Test forecast generation
        forecast = generate_forecast_scenarios("01/01/2024", "01/02/2024")
        print(f"[OK] Forecast generation test passed: {len(forecast.rain)} rain data points")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Timeseries service test failed: {e}")
        return False

def test_node_service():
    """Test node service"""
    print("\nTesting node service...")
    
    try:
        from app.services.node_service import get_available_nodes
        
        nodes_response = get_available_nodes()
        
        if nodes_response["success"]:
            print(f"[OK] Node service test passed: {nodes_response['count']} nodes found")
            if nodes_response["data"]:
                first_node = nodes_response["data"][0]
                print(f"  First node: {first_node['node_id']} ({first_node['node_type']})")
        else:
            print(f"[ERROR] Node service test failed: {nodes_response['message']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"[ERROR] Node service test failed: {e}")
        return False

def test_swmm_service():
    """Test SWMM service (basic test without full simulation)"""
    print("\nTesting SWMM service...")
    
    try:
        from app.services.swmm_service import write_inp
        from app.services.timeseries_service import generate_forecast_scenarios
        
        # Generate test timeseries
        timeseries = generate_forecast_scenarios("01/01/2024", "01/02/2024")
        
        # Test INP file writing
        inp_content = write_inp(timeseries)
        
        if inp_content and len(inp_content) > 1000:
            print("[OK] INP file writing test passed")
        else:
            print("[ERROR] INP file writing test failed: content too short")
            return False
            
        return True
        
    except Exception as e:
        print(f"[ERROR] SWMM service test failed: {e}")
        return False

def test_math_utils():
    """Test math utilities"""
    print("\nTesting math utilities...")
    
    try:
        from app.utils.math_utils import calculate_flood_risk
        
        # Test flood risk calculation
        risk, prob = calculate_flood_risk(2.0, 0.0, 5.0, 10.0)
        print(f"[OK] Flood risk calculation test passed: {risk} ({prob})")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Math utils test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("SWMM Service v2 - System Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_settings,
        test_timeseries_service,
        test_node_service,
        test_swmm_service,
        test_math_utils
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All tests passed! System is ready.")
        return True
    else:
        print("[FAILED] Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
