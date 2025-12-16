"""
Sleep Data Routes - Fetching and predictions
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import json

from services.config import (
    config_store, data_store,
    MQTT_TOPIC_PREDICTIONS
)
from services.database import (
    save_prediction_to_db, get_pending_sync_items, get_pending_count,
    update_prediction_cloud_result
)
from services.mqtt_service import get_mqtt_client, publish_mqtt
from services.fitbit_service import (
    fetch_sleep_list, fetch_sleep, fetch_heart_rate, fetch_activity_for_date
)
from services.model_service import predict_local, predict_cloud, get_local_model
from services.feature_extractor import (
    extract_features_for_local_model, extract_features_for_cloud_model,
    update_lag_features, update_cloud_lag_features, get_sleep_type_info
)
from services.insights_service import log_prediction_to_cloud
from services.iothub_service import report_twin_properties

sleep_bp = Blueprint('sleep', __name__)


@sleep_bp.route('/api/config', methods=['GET', 'POST'])
def config():
    from services.alarm_service import get_alarm_status
    from services.iothub_service import is_connected as iothub_is_connected
    
    if request.method == 'POST':
        data = request.get_json()
        
        if 'cloud_enabled' in data:
            config_store['cloud_enabled'] = data['cloud_enabled']
            report_twin_properties({'cloud_enabled': data['cloud_enabled']})
            
            if data['cloud_enabled']:
                _sync_pending_predictions()
        else:
            for key in ['monitoring_active']:
                if key in data:
                    config_store[key] = data[key]
                    report_twin_properties({key: data[key]})
    
    config_store['pending_sync_count'] = get_pending_count()
    config_store['alarm'] = get_alarm_status()
    config_store['iothub_connected'] = iothub_is_connected()
    return jsonify(config_store)


@sleep_bp.route('/api/data', methods=['GET'])
def get_data():
    limit = request.args.get('limit', 50, type=int)
    return jsonify(data_store[:limit])


@sleep_bp.route('/api/fetch', methods=['POST'])
def fetch_and_predict():
    """Fetch sleep history and make predictions using both local and cloud models."""
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
        prediction = _process_sleep_session(i, session, sessions_reversed, hr_data, activity_cache)
        if prediction:
            data_store.insert(0, prediction)
    
    if data_store:
        return jsonify({
            "latest": data_store[0],
            "total_sessions": len(data_store),
            "message": f"Fetched {len(data_store)} sleep sessions",
            "cloud_available": config_store.get('azure_available', False)
        })
    
    return jsonify({"latest": None, "total_sessions": 0, "message": "No sleep sessions found"})


@sleep_bp.route('/api/fetch/current', methods=['POST'])
def fetch_current():
    """Fetch current sleep data for monitoring."""
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
    cloud_features = extract_features_for_cloud_model(session, hr_data, None, None)
    
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


@sleep_bp.route('/api/predict/cloud', methods=['POST'])
def cloud_predict_endpoint():
    from services.config import AZURE_ENDPOINT_URL
    if not AZURE_ENDPOINT_URL:
        return jsonify({"error": "Azure endpoint not configured"}), 503
    
    data = request.get_json()
    result = predict_cloud(data)
    
    if result:
        return jsonify(result)
    return jsonify({"error": "Cloud prediction failed"}), 503


@sleep_bp.route('/api/sync', methods=['POST'])
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
        
        from services.database import mark_synced
        result = predict_cloud(cloud_features)
        if result:
            mark_synced(prediction_id)
            synced += 1
    
    return jsonify({
        "total_pending": len(pending),
        "synced": synced,
        "remaining": len(pending) - synced
    })


@sleep_bp.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    if not config_store.get('fitbit_connected', False):
        return jsonify({"error": "Fitbit not connected"}), 400
    config_store['monitoring_active'] = True
    return jsonify({"status": "Monitoring started", "monitoring_active": True})


@sleep_bp.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    config_store['monitoring_active'] = False
    return jsonify({"status": "Monitoring stopped", "monitoring_active": False})


@sleep_bp.route('/api/cloud/toggle', methods=['POST'])
def toggle_cloud():
    data = request.get_json() or {}
    enabled = data.get('enabled')
    
    if enabled is None:
        config_store['cloud_enabled'] = not config_store.get('cloud_enabled', True)
    else:
        config_store['cloud_enabled'] = bool(enabled)
    
    report_twin_properties({'cloud_enabled': config_store['cloud_enabled']})
    
    if config_store['cloud_enabled']:
        synced = _sync_pending_predictions()
        config_store['pending_sync_count'] = get_pending_count()
        return jsonify({
            "cloud_enabled": True,
            "synced": synced,
            "pending_remaining": config_store['pending_sync_count']
        })
    
    return jsonify({
        "cloud_enabled": False,
        "pending_count": get_pending_count()
    })


# Helper functions

def _process_sleep_session(i, session, sessions_reversed, hr_data, activity_cache):
    """Process a single sleep session and return prediction."""
    previous_session = sessions_reversed[i - 1] if i > 0 else None
    
    sleep_date = session.get('dateOfSleep', '')
    prev_date = previous_session.get('dateOfSleep', '') if previous_session else ''
    
    # Fetch activity data
    if sleep_date and sleep_date not in activity_cache:
        activity_cache[sleep_date] = fetch_activity_for_date(sleep_date)
    if prev_date and prev_date not in activity_cache:
        activity_cache[prev_date] = fetch_activity_for_date(prev_date)
    
    activity_data = activity_cache.get(sleep_date)
    previous_activity = activity_cache.get(prev_date)
    
    sleep_type_info = get_sleep_type_info(session)
    
    # Extract features
    local_features = extract_features_for_local_model(session, hr_data, previous_session)
    cloud_features = extract_features_for_cloud_model(session, activity_data, previous_session, previous_activity)
    
    print(f"[FEATURES] Session {i+1} ({sleep_type_info['type']}): "
          f"deep_sleep={local_features['deep_sleep_in_minutes']:.1f}, "
          f"rhr={local_features['resting_heart_rate']:.0f}")
    
    # Predictions
    local_result = predict_local(local_features)
    cloud_result = predict_cloud(cloud_features) if config_store.get('cloud_enabled', True) else None
    
    # Update lag features
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
    
    # Build prediction
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
    log_prediction_to_cloud(prediction)
    
    # Publish to MQTT
    mqtt_client = get_mqtt_client()
    if mqtt_client:
        publish_mqtt(MQTT_TOPIC_PREDICTIONS, {
            'timestamp': prediction['timestamp'],
            'quality': prediction['quality'],
            'score': prediction['overall_score'],
            'source': 'cloud' if cloud_result else 'local'
        })
    
    return prediction


def _sync_pending_predictions():
    """Sync pending predictions to cloud. Returns count synced."""
    pending = get_pending_sync_items()
    synced = 0
    
    for item in pending:
        sync_id, prediction_id, payload = item
        pred_data = json.loads(payload)
        cloud_features = extract_features_for_cloud_model(
            {'minutesAsleep': pred_data.get('minutes_asleep', 0)},
            None, None, None
        )
        result = predict_cloud(cloud_features)
        if result:
            update_prediction_cloud_result(
                prediction_id,
                result.get('quality'),
                result.get('confidence'),
                result.get('probabilities')
            )
            log_prediction_to_cloud({**pred_data, **result})
            
            for entry in data_store:
                if entry.get('timestamp') == pred_data.get('timestamp'):
                    entry['cloud_quality'] = result.get('quality')
                    entry['cloud_confidence'] = result.get('confidence')
                    entry['cloud_probabilities'] = result.get('probabilities')
                    entry['quality'] = result.get('quality')
                    break
            
            synced += 1
    
    if synced > 0:
        print(f"[SYNC] Synced {synced} pending predictions")
    
    return synced
