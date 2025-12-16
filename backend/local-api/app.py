"""
Smart Alarm Local API
Handles Fitbit OAuth, data fetching, local predictions, Azure cloud predictions,
MQTT messaging, and SQLite fallback storage.

Architecture:
- Local Model: Random Forest Regression (predicts overall_score 0-100)
- Cloud Model: Random Forest Classifier (predicts quality class: Poor/Fair/Good)
- MQTT: Publishes predictions to IoT broker for edge device consumption
- SQLite: Stores predictions locally when Azure is unavailable
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from urllib.parse import urlencode
import json

from services.config import (
    config_store, data_store,
    FITBIT_CLIENT_ID, FITBIT_REDIRECT_URI,
    MQTT_TOPIC_PREDICTIONS, DB_PATH
)
from services.database import (
    init_database, save_prediction_to_db,
    get_pending_sync_items, mark_synced
)
from services.mqtt_service import (
    init_mqtt, publish_mqtt, get_mqtt_client
)
from services.fitbit_service import (
    fetch_sleep_list, fetch_sleep, fetch_heart_rate, fetch_activity_for_date,
    exchange_code_for_token, save_tokens_to_env, set_tokens,
    get_access_token
)
from services.model_service import (
    load_local_model, predict_local, predict_cloud,
    get_local_model
)
from services.feature_extractor import (
    extract_features_for_local_model, extract_features_for_cloud_model,
    update_lag_features, update_cloud_lag_features, get_sleep_type_info
)

app = Flask(__name__)
CORS(app)

init_database()
init_mqtt()
load_local_model()


@app.route('/', methods=['GET'])
def root_handler():
    code = request.args.get('code')
    if code:
        tokens = exchange_code_for_token(code, FITBIT_REDIRECT_URI)
        if tokens:
            set_tokens(tokens['access_token'], tokens['refresh_token'])
            save_tokens_to_env(tokens['access_token'], tokens['refresh_token'])
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
        return "Token exchange failed", 400
    
    return jsonify({
        "status": "Smart Alarm API Running",
        "local_model_loaded": get_local_model() is not None,
        "fitbit_connected": config_store.get('fitbit_connected', False),
        "azure_available": config_store.get('azure_available', False),
        "mqtt_connected": config_store.get('mqtt_connected', False)
    })


@app.route('/api/auth/login', methods=['GET'])
def fitbit_login():
    params = {
        'client_id': FITBIT_CLIENT_ID,
        'response_type': 'code',
        'scope': 'heartrate activity sleep profile',
        'redirect_uri': FITBIT_REDIRECT_URI
    }
    return jsonify({"auth_url": f'https://www.fitbit.com/oauth2/authorize?{urlencode(params)}'})


@app.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        data = request.get_json()
        config_store.update(data)
    return jsonify(config_store)


@app.route('/api/data', methods=['GET'])
def get_data():
    limit = request.args.get('limit', 50, type=int)
    return jsonify(data_store[:limit])


@app.route('/api/fetch', methods=['POST'])
def fetch_and_predict():
    """
    Fetch sleep history and make predictions using both local and cloud models.
    - Fetches up to 30 sleep sessions from Fitbit
    - Handles both "stages" and "classic" sleep types
    - Runs local prediction for immediate results
    - Attempts cloud prediction for enhanced accuracy
    - Stores results in SQLite if cloud unavailable
    - Publishes to MQTT for edge devices
    """
    if not config_store.get('fitbit_connected', False):
        return jsonify({"error": "Fitbit not connected"}), 400
    
    print("[FETCH] Starting data fetch...")
    
    sleep_list = fetch_sleep_list(30)
    if not sleep_list:
        return jsonify({"error": "Failed to fetch sleep data"}), 500
    
    hr_data = fetch_heart_rate()
    
    sessions = sleep_list.get('sleep', [])
    print(f"[FETCH] Found {len(sessions)} sleep sessions")
    
    data_store.clear()
    
    sessions_reversed = list(reversed(sessions))
    
    activity_cache = {}
    
    for i, session in enumerate(sessions_reversed):
        previous_session = sessions_reversed[i - 1] if i > 0 else None
        
        sleep_date = session.get('dateOfSleep', '')
        prev_date = previous_session.get('dateOfSleep', '') if previous_session else ''
        
        if sleep_date and sleep_date not in activity_cache:
            activity_cache[sleep_date] = fetch_activity_for_date(sleep_date)
        if prev_date and prev_date not in activity_cache:
            activity_cache[prev_date] = fetch_activity_for_date(prev_date)
        
        activity_data = activity_cache.get(sleep_date)
        previous_activity = activity_cache.get(prev_date)
        
        sleep_type_info = get_sleep_type_info(session)
        
        local_features = extract_features_for_local_model(session, hr_data, previous_session)
        cloud_features = extract_features_for_cloud_model(session, activity_data, previous_session, previous_activity)
        
        print(f"[FEATURES] Session {i+1} ({sleep_type_info['type']}): "
              f"deep_sleep={local_features['deep_sleep_in_minutes']:.1f}, "
              f"rhr={local_features['resting_heart_rate']:.0f}, "
              f"steps={cloud_features.get('TotalSteps', 0)}")
        
        local_result = predict_local(local_features)
        cloud_result = predict_cloud(cloud_features)
        
        update_lag_features(
            local_result.get('score'),
            local_features.get('deep_sleep_in_minutes'),
            local_features.get('resting_heart_rate')
        )
        
        if activity_data:
            summary = activity_data.get('summary', {})
            update_cloud_lag_features(
                summary.get('steps'),
                session.get('minutesAsleep'),
                summary.get('caloriesOut'),
                summary.get('veryActiveMinutes')
            )
        
        prediction = {
            'timestamp': session.get('endTime', datetime.now().isoformat()),
            'start_time': session.get('startTime'),
            'date_of_sleep': session.get('dateOfSleep'),
            'duration_hours': round(session.get('duration', 0) / 3600000, 1),
            'efficiency': session.get('efficiency', 0),
            'minutes_asleep': session.get('minutesAsleep', 0),
            'minutes_awake': session.get('minutesAwake', 0),
            'deep_sleep_minutes': local_features.get('deep_sleep_in_minutes', 0),
            'resting_heart_rate': local_features.get('resting_heart_rate', 0),
            'restlessness': round(local_features.get('restlessness', 0), 3),
            'is_main_sleep': session.get('isMainSleep', False),
            'sleep_type': session.get('type', 'classic'),
            'local_quality': local_result.get('quality'),
            'local_score': local_result.get('score'),
            'cloud_quality': cloud_result.get('quality') if cloud_result else None,
            'cloud_confidence': cloud_result.get('confidence') if cloud_result else None,
            'cloud_probabilities': cloud_result.get('probabilities') if cloud_result else None,
            'quality': cloud_result.get('quality') if cloud_result else local_result.get('quality'),
            'overall_score': local_result.get('score'),
            'confidence': cloud_result.get('confidence') if cloud_result else local_result.get('confidence'),
            'features_used': {
                'deep_sleep': local_features['deep_sleep_in_minutes'],
                'rhr': local_features['resting_heart_rate'],
                'restlessness': local_features['restlessness'],
                'score_lag1': local_features['Score_Lag1'],
                'is_estimated': session.get('type', 'classic') == 'classic'
            }
        }
        
        save_prediction_to_db(prediction)
        data_store.insert(0, prediction)
        
        mqtt_client = get_mqtt_client()
        if mqtt_client and config_store.get('mqtt_connected'):
            publish_mqtt(MQTT_TOPIC_PREDICTIONS, {
                'timestamp': prediction['timestamp'],
                'quality': prediction['quality'],
                'score': prediction['overall_score'],
                'source': 'cloud' if cloud_result else 'local'
            })
    
    if data_store:
        return jsonify({
            "latest": data_store[0],
            "total_sessions": len(data_store),
            "message": f"Fetched {len(data_store)} sleep sessions",
            "cloud_available": config_store.get('azure_available', False)
        })
    
    return jsonify({
        "latest": None,
        "total_sessions": 0,
        "message": "No sleep sessions found"
    })


@app.route('/api/fetch/current', methods=['POST'])
def fetch_current():
    if not config_store.get('fitbit_connected', False):
        return jsonify({"error": "Fitbit not connected"}), 400
    
    hr_data = fetch_heart_rate()
    sleep_data = fetch_sleep()
    
    session = None
    if sleep_data and 'sleep' in sleep_data:
        sessions = sleep_data.get('sleep', [])
        if sessions:
            session = sessions[-1]
    
    local_features = extract_features_for_local_model(session, hr_data, None)
    cloud_features = extract_features_for_cloud_model(session, hr_data, None)
    
    local_result = predict_local(local_features)
    cloud_result = predict_cloud(cloud_features)
    
    prediction = {
        'timestamp': datetime.now().isoformat(),
        'resting_heart_rate': local_features.get('resting_heart_rate'),
        'deep_sleep_minutes': local_features.get('deep_sleep_in_minutes'),
        'restlessness': round(local_features.get('restlessness', 0), 3),
        'local_quality': local_result.get('quality'),
        'local_score': local_result.get('score'),
        'cloud_quality': cloud_result.get('quality') if cloud_result else None,
        'cloud_confidence': cloud_result.get('confidence') if cloud_result else None,
        'quality': cloud_result.get('quality') if cloud_result else local_result.get('quality'),
        'overall_score': local_result.get('score'),
        'confidence': cloud_result.get('confidence') if cloud_result else local_result.get('confidence'),
        'is_monitoring': True
    }
    
    save_prediction_to_db(prediction)
    
    data_store.insert(0, prediction)
    if len(data_store) > 100:
        data_store.pop()
    
    mqtt_client = get_mqtt_client()
    if mqtt_client and config_store.get('mqtt_connected'):
        publish_mqtt(MQTT_TOPIC_PREDICTIONS, {
            'timestamp': prediction['timestamp'],
            'quality': prediction['quality'],
            'score': prediction['overall_score'],
            'monitoring': True
        })
    
    return jsonify(prediction)


@app.route('/api/predict/cloud', methods=['POST'])
def cloud_predict_endpoint():
    from services.config import AZURE_ENDPOINT_URL
    if not AZURE_ENDPOINT_URL:
        return jsonify({"error": "Azure endpoint not configured"}), 503
    
    data = request.get_json()
    result = predict_cloud(data)
    
    if result:
        return jsonify(result)
    return jsonify({"error": "Cloud prediction failed"}), 503


@app.route('/api/sync', methods=['POST'])
def sync_pending():
    pending = get_pending_sync_items()
    synced = 0
    
    for item in pending:
        sync_id, prediction_id, payload = item
        data = json.loads(payload)
        
        cloud_features = {
            'deep_sleep_in_minutes': data.get('deep_sleep_minutes', 90),
            'resting_heart_rate': data.get('resting_heart_rate', 65),
            'restlessness': data.get('restlessness', 0.1),
            'DayOfWeek': 3,
            'IsWeekend': 0,
            'WakeupHour': 7,
            'Score_Lag1': 75,
            'DeepSleep_Lag1': 85,
            'RHR_Lag1': 65
        }
        
        result = predict_cloud(cloud_features)
        if result:
            mark_synced(prediction_id)
            synced += 1
    
    return jsonify({
        "total_pending": len(pending),
        "synced": synced,
        "remaining": len(pending) - synced
    })


@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    if not config_store.get('fitbit_connected', False):
        return jsonify({"error": "Fitbit not connected"}), 400
    config_store['monitoring_active'] = True
    return jsonify({"status": "Monitoring started", "monitoring_active": True})


@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    config_store['monitoring_active'] = False
    return jsonify({"status": "Monitoring stopped", "monitoring_active": False})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "local_model_loaded": get_local_model() is not None,
        "fitbit_connected": config_store.get('fitbit_connected', False),
        "azure_available": config_store.get('azure_available', False),
        "mqtt_connected": config_store.get('mqtt_connected', False)
    })


if __name__ == '__main__':
    print("=" * 60)
    print("Smart Alarm Local API Server")
    print("=" * 60)
    print(f"Local Model:     {'Loaded' if get_local_model() else 'Not Found'}")
    print(f"Fitbit:          {'Connected' if config_store.get('fitbit_connected') else 'Not Connected'}")
    from services.config import AZURE_ENDPOINT_URL, MQTT_BROKER, MQTT_PORT
    print(f"Azure Endpoint:  {'Configured' if AZURE_ENDPOINT_URL else 'Not Configured'}")
    print(f"MQTT Broker:     {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Database:        {DB_PATH}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=True)
