"""
Smart Alarm Local API (Refactored)
Main application entry point.

Architecture:
- Routes: Modular route handlers in routes/ package
- Services: Business logic in services/ package
- Local Model: Random Forest Regression (predicts overall_score 0-100)
- Cloud Model: Random Forest Classifier (predicts quality class: Poor/Fair/Good)
- MQTT: Publishes predictions to IoT broker for edge device consumption
- SQLite: Stores predictions locally when Azure is unavailable
"""

from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

from services.config import (
    config_store, DB_PATH,
    MQTT_BROKER, MQTT_PORT, AZURE_ENDPOINT_URL
)
from services.database import init_database, get_pending_count
from services.mqtt_service import init_mqtt, is_mqtt_connected
from services.model_service import load_local_model, get_local_model
from services.insights_service import init_insights
from services.alarm_service import set_alarm, disable_alarm
from services.iothub_service import init_iothub, is_connected as iothub_is_connected

from routes import register_blueprints, handle_oauth_callback

app = Flask(__name__)
CORS(app)


def on_twin_update(patch):
    """Handle IoT Hub twin updates."""
    if 'alarm_enabled' in patch:
        if patch['alarm_enabled']:
            wake_time = patch.get('alarm_wake_time', '07:00')
            window = patch.get('alarm_window_minutes', 30)
            set_alarm(wake_time, window)
        else:
            disable_alarm()


# Initialize services
init_database()
init_mqtt()
init_insights()
init_iothub(update_callback=on_twin_update)
load_local_model()

# Register route blueprints
register_blueprints(app)


# Root and health endpoints (not in blueprints for simplicity)

@app.route('/', methods=['GET'])
def root_handler():
    """Root endpoint - handles OAuth callback and status."""
    code = request.args.get('code')
    if code:
        result = handle_oauth_callback(code)
        if result:
            return result
        return "Token exchange failed - check server logs", 400
    
    return jsonify({
        "status": "Smart Alarm API Running",
        "local_model_loaded": get_local_model() is not None,
        "fitbit_connected": config_store.get('fitbit_connected', False),
        "azure_available": config_store.get('azure_available', False),
        "mqtt_connected": config_store.get('mqtt_connected', False)
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Kubernetes."""
    return jsonify({
        "status": "healthy",
        "local_model_loaded": get_local_model() is not None,
        "fitbit_connected": config_store.get('fitbit_connected', False),
        "azure_available": config_store.get('azure_available', False),
        "cloud_enabled": config_store.get('cloud_enabled', True),
        "mqtt_connected": config_store.get('mqtt_connected', False),
        "iothub_connected": iothub_is_connected(),
        "pending_sync": get_pending_count()
    })


@app.route('/api/debug/iothub', methods=['GET'])
def debug_iothub():
    """Debug endpoint for IoT Hub connectivity."""
    return jsonify({
        'connection_string_loaded': True,
        'client_connected': iothub_is_connected(),
        'twin_sync_enabled': True
    })


@app.route('/api/debug/blob', methods=['GET', 'POST'])
def debug_blob():
    """Debug endpoint for Azure Blob Storage."""
    from services.blob_storage_service import store_prediction, get_storage_status, list_predictions
    
    if request.method == 'POST':
        test_data = {
            'timestamp': datetime.now().isoformat(),
            'test': True,
            'quality': 'Good',
            'score': 85.0
        }
        success = store_prediction(test_data)
        return jsonify({
            'stored': success,
            'test_data': test_data,
            'status': get_storage_status()
        })
    
    return jsonify({
        'status': get_storage_status(),
        'recent_predictions': list_predictions()[:10]
    })


@app.route('/api/debug/mqtt', methods=['GET', 'POST'])
def debug_mqtt():
    """Debug endpoint for MQTT connectivity."""
    from services.mqtt_service import publish_twin_reported
    
    if request.method == 'POST':
        data = request.get_json() or {'test': 'manual_ping'}
        success = publish_twin_reported(data)
        return jsonify({
            'mqtt_connected': is_mqtt_connected(),
            'publish_success': success,
            'payload': data
        })
    
    return jsonify({
        'mqtt_connected': is_mqtt_connected(),
        'broker': f"{MQTT_BROKER}:{MQTT_PORT}"
    })


if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_ENV', 'production') != 'production'
    
    print("=" * 60)
    print("Smart Alarm Local API Server")
    print("=" * 60)
    print(f"Local Model:     {'Loaded' if get_local_model() else 'Not Found'}")
    print(f"Fitbit:          {'Connected' if config_store.get('fitbit_connected') else 'Not Connected'}")
    print(f"Azure Endpoint:  {'Configured' if AZURE_ENDPOINT_URL else 'Not Configured'}")
    print(f"MQTT Broker:     {MQTT_BROKER}:{MQTT_PORT}")
    print(f"IoT Hub:         {'Connected' if iothub_is_connected() else 'Not Connected'}")
    print(f"Database:        {DB_PATH}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=debug_mode)
