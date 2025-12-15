"""
Smart Alarm Local API
Handles Fitbit OAuth, data fetching, and sleep quality predictions.
Uses the local regression model directly (no separate model service needed).
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import numpy as np
import joblib
from urllib.parse import urlencode

# Load from root .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

app = Flask(__name__)
CORS(app)

FITBIT_API_BASE = 'https://api.fitbit.com'
FITBIT_CLIENT_ID = os.getenv('FITBIT_CLIENT_ID', '')
FITBIT_CLIENT_SECRET = os.getenv('FITBIT_CLIENT_SECRET', '')
FITBIT_REDIRECT_URI = os.getenv('FITBIT_REDIRECT_URI', 'http://127.0.0.1:8080')

FITBIT_ACCESS_TOKEN = os.getenv('FITBIT_ACCESS_TOKEN', '')
FITBIT_REFRESH_TOKEN = os.getenv('FITBIT_REFRESH_TOKEN', '')

data_store = []
config_store = {
    'fitbit_connected': bool(FITBIT_ACCESS_TOKEN and FITBIT_ACCESS_TOKEN != ''),
    'monitoring_active': False
}

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'local_model')
model = None
imputer = None

def load_local_model():
    """Load the local regression model for sleep score prediction"""
    global model, imputer
    
    model_path = os.path.join(MODEL_DIR, 'random_forest_regression_model.pkl')
    imputer_path = os.path.join(MODEL_DIR, 'imputer_reg.pkl')
    
    print(f"[MODEL] Looking for model at: {model_path}")
    print(f"[MODEL] Model exists: {os.path.exists(model_path)}")
    
    try:
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            print(f"[MODEL] Loaded regression model")
            print(f"[MODEL] Model expects {model.n_features_in_} features")
        else:
            print(f"[MODEL] WARNING: Model not found!")
            
        if os.path.exists(imputer_path):
            imputer = joblib.load(imputer_path)
            print(f"[MODEL] Loaded imputer")
    except Exception as e:
        print(f"[MODEL] Error loading model: {e}")

load_local_model()

def save_tokens_to_env(access_token, refresh_token):
    """Save tokens to .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith('FITBIT_ACCESS_TOKEN='):
                    f.write(f'FITBIT_ACCESS_TOKEN={access_token}\n')
                elif line.startswith('FITBIT_REFRESH_TOKEN='):
                    f.write(f'FITBIT_REFRESH_TOKEN={refresh_token}\n')
                else:
                    f.write(line)

def refresh_fitbit_token():
    """Refresh Fitbit access token"""
    global FITBIT_ACCESS_TOKEN, FITBIT_REFRESH_TOKEN
    
    if not FITBIT_REFRESH_TOKEN:
        return False
        
    url = 'https://api.fitbit.com/oauth2/token'
    auth = (FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET)
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': FITBIT_REFRESH_TOKEN
    }
    
    try:
        response = requests.post(url, auth=auth, headers=headers, data=data)
        if response.status_code == 200:
            tokens = response.json()
            FITBIT_ACCESS_TOKEN = tokens['access_token']
            FITBIT_REFRESH_TOKEN = tokens['refresh_token']
            save_tokens_to_env(FITBIT_ACCESS_TOKEN, FITBIT_REFRESH_TOKEN)
            config_store['fitbit_connected'] = True
            return True
    except Exception as e:
        print(f"[FITBIT] Token refresh failed: {e}")
    return False

def fetch_fitbit_heart_rate(date=None):
    """Fetch heart rate data from Fitbit API"""
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    url = f'{FITBIT_API_BASE}/1/user/-/activities/heart/date/{date}/1d/1sec.json'
    headers = {'Authorization': f'Bearer {FITBIT_ACCESS_TOKEN}'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 401:
            if refresh_fitbit_token():
                headers = {'Authorization': f'Bearer {FITBIT_ACCESS_TOKEN}'}
                response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        print(f"[FITBIT] HR API returned: {response.status_code}")
    except Exception as e:
        print(f"[FITBIT] Error fetching heart rate: {e}")
    return None

def fetch_fitbit_sleep(date=None):
    """Fetch sleep data from Fitbit API"""
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    url = f'{FITBIT_API_BASE}/1.2/user/-/sleep/date/{date}.json'
    headers = {'Authorization': f'Bearer {FITBIT_ACCESS_TOKEN}'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 401:
            if refresh_fitbit_token():
                headers = {'Authorization': f'Bearer {FITBIT_ACCESS_TOKEN}'}
                response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        print(f"[FITBIT] Sleep API returned: {response.status_code}")
    except Exception as e:
        print(f"[FITBIT] Error fetching sleep: {e}")
    return None

def extract_features_for_model(hr_data=None, sleep_data=None):
    """
    Extract features matching the local model's expected input.
    
    Model was trained on: data/sleep_quality_preprocessed.csv
    Features (in order): revitalization_score, deep_sleep_in_minutes, 
    resting_heart_rate, restlessness, DayOfWeek, IsWeekend, WakeupHour, 
    Score_Lag1, DeepSleep_Lag1, RHR_Lag1
    """
    now = datetime.now()
    
    features = {
        'revitalization_score': 70.0,
        'deep_sleep_in_minutes': 90.0,
        'resting_heart_rate': 65.0,
        'restlessness': 0.1,
        'DayOfWeek': now.weekday(),
        'IsWeekend': 1 if now.weekday() >= 5 else 0,
        'WakeupHour': now.hour,
        'Score_Lag1': 75.0,
        'DeepSleep_Lag1': 90.0,
        'RHR_Lag1': 65.0
    }
    
    if hr_data and 'activities-heart' in hr_data:
        for day_data in hr_data.get('activities-heart', []):
            resting_hr = day_data.get('value', {}).get('restingHeartRate')
            if resting_hr:
                features['resting_heart_rate'] = float(resting_hr)
                features['RHR_Lag1'] = float(resting_hr)
                break
    
    if sleep_data and 'sleep' in sleep_data:
        sleep_records = sleep_data.get('sleep', [])
        if sleep_records:
            latest = sleep_records[-1]
            
            levels = latest.get('levels', {})
            summary = levels.get('summary', {})
            deep = summary.get('deep', {})
            if deep.get('minutes'):
                features['deep_sleep_in_minutes'] = float(deep['minutes'])
                features['DeepSleep_Lag1'] = features['deep_sleep_in_minutes']
            
            wake = summary.get('wake', {})
            wake_minutes = wake.get('minutes', 0)
            total_minutes = latest.get('minutesAsleep', 1)
            if total_minutes > 0:
                features['restlessness'] = float(wake_minutes / total_minutes)
            
            end_time = latest.get('endTime', '')
            if end_time:
                try:
                    wake_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    features['WakeupHour'] = wake_dt.hour
                except:
                    pass
            
            efficiency = latest.get('efficiency', 85)
            features['revitalization_score'] = float(efficiency)
    
    return features

def predict_sleep_quality(features_dict):
    """
    Make prediction using the LOCAL model (from local_model folder).
    Returns prediction result or default if model not available.
    """
    if model is None:
        print("[PREDICT] Model not loaded - returning defaults")
        return {
            "prediction": "unknown",
            "overall_score": 0,
            "confidence": 0,
            "probabilities": {},
            "error": "Model not loaded"
        }
    
    try:
        feature_order = [
            'revitalization_score',
            'deep_sleep_in_minutes', 
            'resting_heart_rate',
            'restlessness',
            'DayOfWeek',
            'IsWeekend',
            'WakeupHour',
            'Score_Lag1',
            'DeepSleep_Lag1',
            'RHR_Lag1'
        ]
        
        features_list = [features_dict[f] for f in feature_order]
        features_array = np.array([features_list])
        
        print(f"[PREDICT] Input features: {features_list}")
        
        if imputer is not None:
            features_array = imputer.transform(features_array)
        
        predicted_score = float(model.predict(features_array)[0])
        print(f"[PREDICT] Predicted score: {predicted_score}")
        
        if predicted_score >= 85:
            quality = "excellent"
        elif predicted_score >= 70:
            quality = "good"
        elif predicted_score >= 55:
            quality = "fair"
        else:
            quality = "poor"
        
        return {
            "prediction": quality,
            "overall_score": round(predicted_score, 1),
            "confidence": round(min(predicted_score / 100, 1.0), 2),
            "probabilities": {
                "excellent": 1.0 if quality == "excellent" else 0.0,
                "good": 1.0 if quality == "good" else 0.0,
                "fair": 1.0 if quality == "fair" else 0.0,
                "poor": 1.0 if quality == "poor" else 0.0
            }
        }
    except Exception as e:
        print(f"[PREDICT] Error: {e}")
        return {
            "prediction": "error",
            "overall_score": 0,
            "confidence": 0,
            "probabilities": {},
            "error": str(e)
        }

@app.route('/', methods=['GET'])
def root_handler():
    """Handle OAuth callback or show home page"""
    global FITBIT_ACCESS_TOKEN, FITBIT_REFRESH_TOKEN
    
    code = request.args.get('code')
    if code:
        url = 'https://api.fitbit.com/oauth2/token'
        auth = (FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'client_id': FITBIT_CLIENT_ID,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': FITBIT_REDIRECT_URI
        }
        
        try:
            response = requests.post(url, auth=auth, headers=headers, data=data)
            if response.status_code == 200:
                tokens = response.json()
                FITBIT_ACCESS_TOKEN = tokens['access_token']
                FITBIT_REFRESH_TOKEN = tokens['refresh_token']
                save_tokens_to_env(FITBIT_ACCESS_TOKEN, FITBIT_REFRESH_TOKEN)
                config_store['fitbit_connected'] = True
                
                return """
                <html>
                    <body style="font-family: Arial; text-align: center; padding: 50px;">
                        <h2 style="color: #28a745;">Fitbit Connected Successfully!</h2>
                        <p>You can close this window and return to the dashboard.</p>
                        <script>setTimeout(() => window.close(), 2000);</script>
                    </body>
                </html>
                """
            else:
                return f"Token exchange failed: {response.text}", 400
        except Exception as e:
            return f"Error: {str(e)}", 500
    
    return jsonify({
        "status": "Smart Alarm API Running",
        "model_loaded": model is not None,
        "fitbit_connected": config_store.get('fitbit_connected', False)
    })

@app.route('/api/auth/login', methods=['GET'])
def fitbit_login():
    """Initiate Fitbit OAuth flow"""
    params = {
        'client_id': FITBIT_CLIENT_ID,
        'response_type': 'code',
        'scope': 'heartrate activity sleep profile',
        'redirect_uri': FITBIT_REDIRECT_URI
    }
    auth_url = f'https://www.fitbit.com/oauth2/authorize?{urlencode(params)}'
    return jsonify({"auth_url": auth_url})

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """Get or update configuration"""
    if request.method == 'POST':
        data = request.get_json()
        config_store.update(data)
    return jsonify(config_store)

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get stored predictions"""
    limit = request.args.get('limit', 50, type=int)
    return jsonify(data_store[:limit])

@app.route('/api/fetch', methods=['POST'])
def fetch_and_predict():
    """
    Fetch historical sleep data from Fitbit and make predictions.
    Returns sleep quality predictions for recent sleep sessions (up to last 30 days available in one request).
    """
    if not config_store.get('fitbit_connected', False):
        return jsonify({"error": "Fitbit not connected. Please connect first."}), 400
    
    print("[FETCH] Starting historical data fetch...")
    
    url = f'{FITBIT_API_BASE}/1.2/user/-/sleep/list.json?beforeDate={datetime.now().strftime("%Y-%m-%d")}&sort=desc&offset=0&limit=30'
    headers = {'Authorization': f'Bearer {FITBIT_ACCESS_TOKEN}'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 401:
            if refresh_fitbit_token():
                headers = {'Authorization': f'Bearer {FITBIT_ACCESS_TOKEN}'}
                response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[FETCH] Sleep list API returned: {response.status_code}")
            return jsonify({"error": f"Fitbit API error: {response.status_code}"}), 500
            
        sleep_list = response.json()
    except Exception as e:
        print(f"[FETCH] Error fetching sleep list: {e}")
        return jsonify({"error": str(e)}), 500
    
    hr_data = fetch_fitbit_heart_rate()
    
    sessions = sleep_list.get('sleep', [])
    print(f"[FETCH] Found {len(sessions)} sleep sessions")
    
    data_store.clear()
    
    for session in sessions:
        features = extract_features_from_sleep_session(session, hr_data)
        
        prediction_result = predict_sleep_quality(features)
        
        data_entry = {
            'timestamp': session.get('endTime', datetime.now().isoformat()),
            'start_time': session.get('startTime'),
            'duration_hours': round(session.get('duration', 0) / 3600000, 1),  # ms to hours
            'efficiency': session.get('efficiency', 0),
            'minutes_asleep': session.get('minutesAsleep', 0),
            'minutes_awake': session.get('minutesAwake', 0),
            'deep_sleep_minutes': features.get('deep_sleep_in_minutes', 0),
            'resting_heart_rate': features.get('resting_heart_rate', 0),
            'restlessness': round(features.get('restlessness', 0), 3),
            'quality': prediction_result.get('prediction', 'unknown'),
            'overall_score': prediction_result.get('overall_score', 0),
            'confidence': prediction_result.get('confidence', 0),
            'is_main_sleep': session.get('isMainSleep', False)
        }
        
        data_store.append(data_entry)
    
    if data_store:
        return jsonify({
            "latest": data_store[0],
            "total_sessions": len(data_store),
            "message": f"Fetched {len(data_store)} sleep sessions"
        })
    else:
        return jsonify({
            "latest": None,
            "total_sessions": 0,
            "message": "No sleep sessions found"
        })


def extract_features_from_sleep_session(session, hr_data=None):
    """Extract features from a single Fitbit sleep session"""
    now = datetime.now()
    
    features = {
        'revitalization_score': 70.0,
        'deep_sleep_in_minutes': 90.0,
        'resting_heart_rate': 65.0,
        'restlessness': 0.1,
        'DayOfWeek': now.weekday(),
        'IsWeekend': 1 if now.weekday() >= 5 else 0,
        'WakeupHour': now.hour,
        'Score_Lag1': 75.0,
        'DeepSleep_Lag1': 90.0,
        'RHR_Lag1': 65.0
    }
    
    end_time = session.get('endTime', '')
    if end_time:
        try:
            wake_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00').replace('+00:00', ''))
            features['WakeupHour'] = wake_dt.hour
            features['DayOfWeek'] = wake_dt.weekday()
            features['IsWeekend'] = 1 if wake_dt.weekday() >= 5 else 0
        except:
            pass
    
    levels = session.get('levels', {})
    summary = levels.get('summary', {})
    deep = summary.get('deep', {})
    if deep.get('minutes'):
        features['deep_sleep_in_minutes'] = float(deep['minutes'])
        features['DeepSleep_Lag1'] = features['deep_sleep_in_minutes']
    
    wake = summary.get('wake', {})
    wake_minutes = wake.get('minutes', 0)
    total_minutes = session.get('minutesAsleep', 1)
    if total_minutes > 0:
        features['restlessness'] = float(wake_minutes / total_minutes)
    
    efficiency = session.get('efficiency', 85)
    features['revitalization_score'] = float(efficiency)
    
    if hr_data and 'activities-heart' in hr_data:
        for day_data in hr_data.get('activities-heart', []):
            resting_hr = day_data.get('value', {}).get('restingHeartRate')
            if resting_hr:
                features['resting_heart_rate'] = float(resting_hr)
                features['RHR_Lag1'] = float(resting_hr)
                break
    
    return features


@app.route('/api/fetch/current', methods=['POST'])  
def fetch_current():
    """
    Fetch just the current/latest reading (for monitoring mode).
    This is a lighter endpoint that only gets today's data.
    """
    if not config_store.get('fitbit_connected', False):
        return jsonify({"error": "Fitbit not connected"}), 400
    
    hr_data = fetch_fitbit_heart_rate()
    sleep_data = fetch_fitbit_sleep()
    
    features = extract_features_for_model(hr_data, sleep_data)
    prediction_result = predict_sleep_quality(features)
    
    data_entry = {
        'timestamp': datetime.now().isoformat(),
        'resting_heart_rate': features.get('resting_heart_rate'),
        'deep_sleep_minutes': features.get('deep_sleep_in_minutes'),
        'restlessness': round(features.get('restlessness', 0), 3),
        'quality': prediction_result.get('prediction', 'unknown'),
        'overall_score': prediction_result.get('overall_score', 0),
        'confidence': prediction_result.get('confidence', 0),
        'is_monitoring': True
    }
    
    data_store.insert(0, data_entry)
    if len(data_store) > 100:
        data_store.pop()
    
    return jsonify(data_entry)

@app.route('/api/predict', methods=['POST'])
def manual_predict():
    """Make prediction with provided features"""
    data = request.get_json()
    
    features = extract_features_for_model()
    features.update({k: v for k, v in data.items() if k in features})
    
    result = predict_sleep_quality(features)
    return jsonify(result)

@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    """Start monitoring mode"""
    if not config_store.get('fitbit_connected', False):
        return jsonify({"error": "Please connect Fitbit first"}), 400
    config_store['monitoring_active'] = True
    return jsonify({"status": "Monitoring started", "monitoring_active": True})

@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Stop monitoring mode"""
    config_store['monitoring_active'] = False
    return jsonify({"status": "Monitoring stopped", "monitoring_active": False})

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
        "fitbit_connected": config_store.get('fitbit_connected', False)
    })

if __name__ == '__main__':
    print("=" * 60)
    print("Smart Alarm Local API Server")
    print("=" * 60)
    print(f"Model loaded: {model is not None}")
    print(f"Fitbit connected: {config_store.get('fitbit_connected', False)}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=True)
