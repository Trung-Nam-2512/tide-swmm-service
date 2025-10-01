#!/usr/bin/env python3
"""
Test script to verify API endpoints are working
"""

import requests
import json
import time

def test_api_endpoints():
    """Test the main API endpoints"""
    base_url = "http://127.0.0.1:8000"
    
    print("Testing SWMM API endpoints...")
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/swmm-api/health")
        if response.status_code == 200:
            print("Health check: OK")
        else:
            print(f"Health check failed: {response.status_code}")
    except Exception as e:
        print(f"Health check error: {e}")
    
    # Test 2: Available nodes
    try:
        response = requests.get(f"{base_url}/swmm-api/available-nodes")
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('count', 0) > 0:
                print(f"Available nodes: OK ({data['count']} nodes)")
            else:
                print(f"Available nodes failed: {data}")
        else:
            print(f"Available nodes failed: {response.status_code}")
    except Exception as e:
        print(f"Available nodes error: {e}")
    
    # Test 3: Water level forecast (simple test)
    try:
        params = {
            "start_date": "10/01/2025",
            "end_date": "10/02/2025",
            "use_cached": "false",
            "force_run": "true"
        }
        response = requests.get(f"{base_url}/swmm-api/water-level-forecast", params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and len(data.get('data', [])) > 0:
                print(f"Water level forecast: OK ({len(data['data'])} nodes)")
            else:
                print(f"Water level forecast failed: {data}")
        else:
            print(f"Water level forecast failed: {response.status_code}")
    except Exception as e:
        print(f"Water level forecast error: {e}")

if __name__ == "__main__":
    print("Starting API tests...")
    test_api_endpoints()
    print("API tests completed!")
