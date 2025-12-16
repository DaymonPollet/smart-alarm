"""
Routes Package - Modular route handlers
"""
import threading
import time
from datetime import datetime

from services.config import config_store, MQTT_TOPIC_ALERTS, MQTT_TOPIC_PREDICTIONS
from services.fitbit_service import fetch_sleep, fetch_heart_rate
from services.model_service import predict_local
from services.feature_extractor import extract_features_for_local_model
from services.mqtt_service import get_mqtt_client, publish_mqtt
from services.alarm_service import check_alarm_trigger, get_alarm_status, alarm_config
from services.database import save_alarm_event

from .auth_routes import auth_bp, handle_oauth_callback
from .alarm_routes import alarm_bp, set_last_fetch_result
from .sleep_routes import sleep_bp

# Background fetch thread management
_background_fetch_thread = None
_stop_background_fetch = False


def _background_fetch_loop():
    """Background loop for sleep monitoring during alarm."""
    global _stop_background_fetch
    
    while not _stop_background_fetch:
        if config_store.get('fitbit_connected') and alarm_config.get('enabled') and not alarm_config.get('triggered'):
            try:
                sleep_data = fetch_sleep()
                hr_data = fetch_heart_rate()
                
                session = None
                if sleep_data and 'sleep' in sleep_data:
                    sessions = sleep_data.get('sleep', [])
                    if sessions:
                        session = sessions[-1]
                
                if session:
                    local_features = extract_features_for_local_model(session, hr_data, None)
                    local_result = predict_local(local_features)
                    
                    is_light = local_result.get('quality', '').lower() in ['fair', 'poor']
                    sleep_quality = local_result.get('quality')
                    sleep_score = local_result.get('score')
                    
                    set_last_fetch_result({
                        'timestamp': datetime.now().isoformat(),
                        'quality': sleep_quality,
                        'score': sleep_score,
                        'is_light_sleep': is_light
                    })
                    
                    alarm_status = get_alarm_status()
                    if alarm_status.get('in_window'):
                        trigger_result = check_alarm_trigger(sleep_quality, is_light)
                        
                        if trigger_result and trigger_result.get('trigger'):
                            save_alarm_event(
                                event_type='triggered',
                                trigger_reason=trigger_result.get('reason'),
                                scheduled_time=alarm_config.get('wake_time'),
                                sleep_quality=sleep_quality,
                                sleep_score=sleep_score,
                                window_minutes=alarm_config.get('window_minutes')
                            )
                            
                            mqtt_client = get_mqtt_client()
                            if mqtt_client:
                                publish_mqtt(MQTT_TOPIC_ALERTS, {
                                    'type': 'alarm_triggered',
                                    'reason': trigger_result.get('reason'),
                                    'time': trigger_result.get('time'),
                                    'quality': sleep_quality,
                                    'score': sleep_score
                                })
                            
                            print(f"[ALARM] Triggered: {trigger_result.get('reason')} - Quality: {sleep_quality}")
                    
                    print(f"[BGFETCH] Quality: {sleep_quality}, Score: {sleep_score:.1f}, Light: {is_light}")
                    
            except Exception as e:
                print(f"[BGFETCH] Error: {e}")
        
        time.sleep(90)


def start_background_fetch():
    """Start background fetch thread for alarm monitoring."""
    global _background_fetch_thread, _stop_background_fetch
    
    if _background_fetch_thread and _background_fetch_thread.is_alive():
        return
    
    _stop_background_fetch = False
    _background_fetch_thread = threading.Thread(target=_background_fetch_loop, daemon=True)
    _background_fetch_thread.start()
    print("[BGFETCH] Background fetch started (90s interval)")


def stop_background_fetch():
    """Stop background fetch thread."""
    global _stop_background_fetch
    _stop_background_fetch = True
    print("[BGFETCH] Background fetch stopped")


def register_blueprints(app):
    """Register all route blueprints with the Flask app."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(alarm_bp)
    app.register_blueprint(sleep_bp)
