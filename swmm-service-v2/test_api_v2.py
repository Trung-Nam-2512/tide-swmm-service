"""
Test API endpoints for SWMM Service v2
"""

import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:1433"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("[OK] Health check passed")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"[ERROR] Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Health check failed: {e}")
        return False

def test_available_nodes():
    """Test available nodes endpoint"""
    print("\nTesting available nodes endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/swmm-api/available-nodes")
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Available nodes test passed: {data['count']} nodes found")
            if data["data"]:
                first_node = data["data"][0]
                print(f"  First node: {first_node['node_id']} ({first_node['node_type']})")
            return True
        else:
            print(f"[ERROR] Available nodes test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Available nodes test failed: {e}")
        return False

def test_water_level_forecast():
    """Test water level forecast endpoint"""
    print("\nTesting water level forecast endpoint...")
    try:
        params = {
            "start_date": "01/01/2024",
            "end_date": "01/02/2024",
            "use_cached": False,
            "force_run": True
        }
        
        response = requests.get(f"{BASE_URL}/water-level-forecast", params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"[OK] Water level forecast test passed: {data['count']} nodes forecasted")
                return True
            else:
                print(f"[ERROR] Water level forecast failed: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"[ERROR] Water level forecast test failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Water level forecast test failed: {e}")
        return False

def main():
    """Run all API tests"""
    print("=" * 50)
    print("SWMM Service v2 - API Test")
    print("=" * 50)
    
    # Wait a moment for server to start
    print("Waiting for server to start...")
    time.sleep(3)
    
    tests = [
        test_health,
        test_available_nodes,
        test_water_level_forecast
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"API Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All API tests passed!")
        return True
    else:
        print("[FAILED] Some API tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
