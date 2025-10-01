"""
Direct test of SWMM Service v2 without server
"""

import sys
import os
import json

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_direct_forecast():
    """Test forecast functionality directly"""
    print("Testing direct forecast functionality...")
    
    try:
        from app.services.timeseries_service import generate_forecast_scenarios
        from app.services.swmm_service import write_inp, run_and_parse_swmm
        from app.services.node_service import get_available_nodes
        
        # Test 1: Generate forecast scenarios
        print("1. Generating forecast scenarios...")
        timeseries = generate_forecast_scenarios("01/01/2024", "01/02/2024")
        print(f"   [OK] Generated {len(timeseries.rain)} rain data points")
        
        # Test 2: Write INP file
        print("2. Writing INP file...")
        inp_content = write_inp(timeseries)
        print(f"   [OK] INP file written ({len(inp_content)} characters)")
        
        # Test 3: Get available nodes
        print("3. Getting available nodes...")
        nodes_response = get_available_nodes()
        if nodes_response["success"]:
            print(f"   [OK] Found {nodes_response['count']} nodes")
        else:
            print(f"   [ERROR] Failed to get nodes: {nodes_response['message']}")
            return False
        
        # Test 4: Run SWMM simulation (this might take a while)
        print("4. Running SWMM simulation...")
        print("   (This may take a few minutes...)")
        
        try:
            results = run_and_parse_swmm()
            if results:
                print(f"   [OK] Simulation completed with {len(results)} node results")
                
                # Show sample results
                if results:
                    sample_result = results[0]
                    print(f"   Sample result for node {sample_result['node']}:")
                    print(f"     - Max depth: {sample_result['max_depth_m']:.2f}m")
                    print(f"     - Max water level: {sample_result['max_water_level_m']:.2f}m")
                    print(f"     - Time series points: {len(sample_result['time_series'])}")
                
                return True
            else:
                print("   [ERROR] Simulation returned no results")
                return False
        except Exception as e:
            print(f"   [ERROR] Simulation failed: {e}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Direct test failed: {e}")
        return False

def main():
    """Run direct test"""
    print("=" * 60)
    print("SWMM Service v2 - Direct Functionality Test")
    print("=" * 60)
    
    success = test_direct_forecast()
    
    print("=" * 60)
    if success:
        print("[SUCCESS] Direct functionality test passed!")
        print("The refactored system is working correctly.")
    else:
        print("[FAILED] Direct functionality test failed.")
        print("Please check the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
