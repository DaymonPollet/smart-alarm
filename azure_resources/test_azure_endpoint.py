"""
Test script for Azure ML Sleep Quality Endpoint
Use this to verify your deployed endpoint is working correctly.
"""

import requests
import json
import os

# Load endpoint info if available
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
endpoint_info_path = os.path.join(SCRIPT_DIR, "endpoint_info.json")

# Default endpoint (update after deployment)
SCORING_URI = "https://fitbit-sleep-alarm-endpoint.westeurope.inference.ml.azure.com/score"
API_KEY = "YOUR_API_KEY_HERE"  # Get from Azure ML Studio

# Try to load from endpoint_info.json
if os.path.exists(endpoint_info_path):
    with open(endpoint_info_path, "r") as f:
        info = json.load(f)
        SCORING_URI = info.get("scoring_uri", SCORING_URI)
        print(f"Loaded endpoint: {SCORING_URI}")

def get_api_key():
    """Get API key from Azure ML - you need to get this from Azure Portal"""
    # You can get the API key from:
    # 1. Azure ML Studio > Endpoints > fitbit-sleep-alarm-endpoint > Consume
    # 2. Or use Azure CLI: az ml online-endpoint get-credentials --name fitbit-sleep-alarm-endpoint
    return API_KEY

def test_prediction():
    """Send a test prediction request"""
    
    # Sample input data (matching the expected features)
    test_data = {
        "data": [
            {
                "deep_sleep_in_minutes": 95,
                "resting_heart_rate": 62,
                "restlessness": 0.08,
                "DayOfWeek": 1,  # Tuesday
                "IsWeekend": 0,
                "WakeupHour": 7,
                "Score_Lag1": 78,
                "DeepSleep_Lag1": 88,
                "RHR_Lag1": 63
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_api_key()}"
    }
    
    print("Testing Azure ML Endpoint...")
    print(f"URL: {SCORING_URI}")
    print(f"Input: {json.dumps(test_data, indent=2)}")
    print("-" * 50)
    
    try:
        response = requests.post(
            SCORING_URI,
            headers=headers,
            json=test_data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Prediction Result:")
            print(json.dumps(result, indent=2))
            
            # Parse and display nicely
            if isinstance(result, list) and len(result) > 0:
                pred = result[0]
                print("\n" + "=" * 50)
                print(f"Sleep Quality: {pred.get('prediction', 'N/A').upper()}")
                print(f"Confidence: {pred.get('confidence', 0) * 100:.1f}%")
                if 'probabilities' in pred:
                    print("Probabilities:")
                    for label, prob in pred['probabilities'].items():
                        print(f"  - {label}: {prob * 100:.1f}%")
                print("=" * 50)
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

def test_multiple_scenarios():
    """Test different sleep scenarios"""
    
    scenarios = [
        {
            "name": "Good Sleep Night",
            "data": {
                "deep_sleep_in_minutes": 100,
                "resting_heart_rate": 58,
                "restlessness": 0.05,
                "DayOfWeek": 6,  # Saturday
                "IsWeekend": 1,
                "WakeupHour": 9,
                "Score_Lag1": 82,
                "DeepSleep_Lag1": 95,
                "RHR_Lag1": 59
            }
        },
        {
            "name": "Poor Sleep Night",
            "data": {
                "deep_sleep_in_minutes": 45,
                "resting_heart_rate": 72,
                "restlessness": 0.25,
                "DayOfWeek": 0,  # Monday
                "IsWeekend": 0,
                "WakeupHour": 5,
                "Score_Lag1": 55,
                "DeepSleep_Lag1": 50,
                "RHR_Lag1": 70
            }
        },
        {
            "name": "Average Sleep Night",
            "data": {
                "deep_sleep_in_minutes": 75,
                "resting_heart_rate": 65,
                "restlessness": 0.12,
                "DayOfWeek": 3,  # Wednesday
                "IsWeekend": 0,
                "WakeupHour": 7,
                "Score_Lag1": 70,
                "DeepSleep_Lag1": 70,
                "RHR_Lag1": 64
            }
        }
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_api_key()}"
    }
    
    print("Testing Multiple Sleep Scenarios")
    print("=" * 60)
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        print("-" * 40)
        
        try:
            response = requests.post(
                SCORING_URI,
                headers=headers,
                json={"data": [scenario['data']]},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    pred = result[0]
                    print(f"  Prediction: {pred.get('prediction', 'N/A').upper()}")
                    print(f"  Confidence: {pred.get('confidence', 0) * 100:.1f}%")
            else:
                print(f"  Error: {response.status_code}")
                
        except Exception as e:
            print(f"  Failed: {e}")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Azure ML Endpoint Test")
    print("=" * 60 + "\n")
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("WARNING: You need to set your API key first!")
        print("Get it from Azure ML Studio > Endpoints > Consume")
        print("\nOr update API_KEY in this script.")
        print("\n" + "-" * 60)
    
    test_prediction()
    
    print("\n\nRunning multiple scenario tests...")
    # test_multiple_scenarios()  # Uncomment to run all scenarios
