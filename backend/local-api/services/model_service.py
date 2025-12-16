import os
import numpy as np
import joblib
import requests
from .config import MODEL_DIR, AZURE_ENDPOINT_URL, AZURE_ENDPOINT_KEY, config_store

local_model = None
local_imputer = None

def load_local_model():
    global local_model, local_imputer
    
    model_path = os.path.join(MODEL_DIR, 'random_forest_regression_model.pkl')
    imputer_path = os.path.join(MODEL_DIR, 'imputer_reg.pkl')
    
    print(f"[MODEL] Loading local model from: {model_path}")
    
    try:
        if os.path.exists(model_path):
            local_model = joblib.load(model_path)
            print(f"[MODEL] Loaded regression model ({local_model.n_features_in_} features)")
        
        if os.path.exists(imputer_path):
            local_imputer = joblib.load(imputer_path)
            print("[MODEL] Loaded imputer")
    except Exception as e:
        print(f"[MODEL] Error loading model: {e}")

def get_local_model():
    return local_model

def get_local_imputer():
    return local_imputer

def predict_local(features_dict):
    if local_model is None:
        return {"quality": "unknown", "score": 0, "error": "Model not loaded"}
    
    try:
        feature_order = [
            'revitalization_score', 'deep_sleep_in_minutes', 'resting_heart_rate',
            'restlessness', 'DayOfWeek', 'IsWeekend', 'WakeupHour',
            'Score_Lag1', 'DeepSleep_Lag1', 'RHR_Lag1'
        ]
        
        features_array = np.array([[features_dict[f] for f in feature_order]])
        
        if local_imputer is not None:
            features_array = local_imputer.transform(features_array)
        
        score = float(local_model.predict(features_array)[0])
        
        if score >= 85:
            quality = "excellent"
        elif score >= 70:
            quality = "good"
        elif score >= 55:
            quality = "fair"
        else:
            quality = "poor"
        
        return {
            "quality": quality,
            "score": round(score, 1),
            "confidence": round(min(score / 100, 1.0), 2)
        }
    except Exception as e:
        print(f"[LOCAL] Prediction error: {e}")
        return {"quality": "error", "score": 0, "error": str(e)}

def predict_cloud(features_dict):
    if not AZURE_ENDPOINT_URL or not AZURE_ENDPOINT_KEY:
        return None
    
    try:
        payload = {"data": [features_dict]}
        
        response = requests.post(
            AZURE_ENDPOINT_URL,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {AZURE_ENDPOINT_KEY}'
            },
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            # Azure returns a JSON string that needs to be parsed again -> if not this will make the model appear like it's offline
            if isinstance(results, str):
                import json
                results = json.loads(results)
            if results and len(results) > 0:
                result = results[0]
                config_store['azure_available'] = True
                return {
                    "quality": result.get('prediction', 'unknown'),
                    "confidence": result.get('confidence', 0),
                    "probabilities": result.get('probabilities', {})
                }
        else:
            print(f"[CLOUD] Azure returned {response.status_code}: {response.text}")
            config_store['azure_available'] = False
    except requests.exceptions.Timeout:
        print("[CLOUD] Azure request timeout")
        config_store['azure_available'] = False
    except requests.exceptions.ConnectionError:
        print("[CLOUD] Azure connection error")
        config_store['azure_available'] = False
    except Exception as e:
        print(f"[CLOUD] Prediction error: {e}")
        config_store['azure_available'] = False
    
    return None
