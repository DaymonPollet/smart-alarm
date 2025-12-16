"""
Alarm Routes - Smart alarm management
"""
from flask import Blueprint, request, jsonify
from datetime import datetime

from services.config import config_store, MQTT_TOPIC_ALERTS
from services.database import save_alarm_event, get_alarm_history
from services.mqtt_service import get_mqtt_client, publish_mqtt
from services.alarm_service import (
    set_alarm, disable_alarm, dismiss_alarm, snooze_alarm,
    check_alarm_trigger, get_alarm_status, alarm_config
)
from services.iothub_service import update_alarm_twin

alarm_bp = Blueprint('alarm', __name__)

# Background fetch state (shared with main app)
last_fetch_result = {}


def set_last_fetch_result(result):
    global last_fetch_result
    last_fetch_result = result


def get_last_fetch_result():
    return last_fetch_result


@alarm_bp.route('/api/alarm', methods=['GET', 'POST', 'DELETE'])
def alarm_endpoint():
    if request.method == 'GET':
        status = get_alarm_status()
        status['last_fetch'] = last_fetch_result
        return jsonify(status)
    
    elif request.method == 'POST':
        data = request.get_json()
        wake_time = data.get('wake_time')
        window_minutes = data.get('window_minutes', 30)
        
        if not wake_time:
            return jsonify({"error": "wake_time required (HH:MM format)"}), 400
        
        if set_alarm(wake_time, window_minutes):
            save_alarm_event(
                event_type='set',
                scheduled_time=wake_time,
                window_minutes=window_minutes
            )
            
            # Import here to avoid circular dependency
            from routes import start_background_fetch
            start_background_fetch()
            
            status = get_alarm_status()
            update_alarm_twin(True, wake_time, window_minutes)
            
            mqtt_client = get_mqtt_client()
            if mqtt_client:
                publish_mqtt(MQTT_TOPIC_ALERTS, {
                    'type': 'alarm_set',
                    'wake_time': wake_time,
                    'window_minutes': window_minutes
                })
            
            return jsonify({"status": "Alarm set", **status})
        return jsonify({"error": "Invalid time format. Use HH:MM"}), 400
    
    elif request.method == 'DELETE':
        disable_alarm()
        from routes import stop_background_fetch
        stop_background_fetch()
        save_alarm_event(event_type='disabled')
        update_alarm_twin(False)
        return jsonify({"status": "Alarm disabled"})


@alarm_bp.route('/api/alarm/snooze', methods=['POST'])
def alarm_snooze():
    data = request.get_json() or {}
    minutes = data.get('minutes', 9)
    new_time = snooze_alarm(minutes)
    
    if new_time:
        save_alarm_event(event_type='snoozed', scheduled_time=new_time)
        
        mqtt_client = get_mqtt_client()
        if mqtt_client:
            publish_mqtt(MQTT_TOPIC_ALERTS, {
                'type': 'alarm_snoozed',
                'new_wake_time': new_time
            })
        return jsonify({"status": "Alarm snoozed", "new_wake_time": new_time})
    return jsonify({"error": "No active alarm to snooze"}), 400


@alarm_bp.route('/api/alarm/dismiss', methods=['POST'])
def alarm_dismiss():
    save_alarm_event(event_type='dismissed')
    dismiss_alarm()
    
    mqtt_client = get_mqtt_client()
    if mqtt_client:
        publish_mqtt(MQTT_TOPIC_ALERTS, {'type': 'alarm_dismissed'})
    
    return jsonify({"status": "Alarm dismissed"})


@alarm_bp.route('/api/alarm/history', methods=['GET'])
def alarm_history():
    limit = request.args.get('limit', 50, type=int)
    history = get_alarm_history(limit)
    return jsonify(history)


@alarm_bp.route('/api/alarm/check', methods=['POST'])
def alarm_check():
    data = request.get_json() or {}
    sleep_quality = data.get('sleep_quality')
    is_light_sleep = data.get('is_light_sleep', False)
    
    result = check_alarm_trigger(sleep_quality, is_light_sleep)
    
    if result and result.get('trigger'):
        save_alarm_event(
            event_type='triggered',
            trigger_reason=result.get('reason'),
            scheduled_time=alarm_config.get('wake_time'),
            sleep_quality=sleep_quality,
            window_minutes=alarm_config.get('window_minutes')
        )
        
        mqtt_client = get_mqtt_client()
        if mqtt_client:
            publish_mqtt(MQTT_TOPIC_ALERTS, {
                'type': 'alarm_triggered',
                'reason': result.get('reason'),
                'time': result.get('time')
            })
        return jsonify({"alarm_triggered": True, **result})
    
    return jsonify({"alarm_triggered": False, "status": get_alarm_status()})
