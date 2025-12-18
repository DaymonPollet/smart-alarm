"""
Azure IoT Hub Device Twin Service
Handles bidirectional configuration sync between the edge device and Azure cloud.
Refactored to use an "Outgoing Buffer" pattern to prevent message floods.
"""
import json
import threading
import time
import logging
import sys
import os
from dotenv import load_dotenv
from .config import config_store

# Suppress noisy Azure IoT device logging
logging.getLogger('azure.iot.device').setLevel(logging.CRITICAL)

# Global State
IOTHUB_CONNECTION_STRING = None
IOTHUB_AVAILABLE = False
device_client = None
twin_update_callback = None
stop_twin_listener = False
twin_listener_thread = None

# Outgoing Buffer & Rate Limiting
_pending_report = {}  # The "Outgoing Buffer"
_last_report_time = 0
_MIN_REPORT_INTERVAL = 60  # Flush at most once every 60 seconds
_lock = threading.Lock()  # Thread safety for buffer access

# Circuit Breaker
_message_count = 0
_message_count_window = 0
_MAX_MESSAGES_PER_MINUTE = 10
_circuit_breaker_tripped = False
_circuit_breaker_reset_time = 0
_CIRCUIT_BREAKER_COOLDOWN = 300  # 5 minutes cooldown

# MQTT Rate Limiting
_last_mqtt_publish_time = 0
_MIN_MQTT_INTERVAL = 5

def init_iothub(update_callback=None):
    """Initialize IoT Hub connection with Device Twin bidirectional sync."""
    global device_client, twin_update_callback, twin_listener_thread, stop_twin_listener
    global IOTHUB_CONNECTION_STRING, IOTHUB_AVAILABLE

    load_dotenv()
    # Use DEVICE connection string (has DeviceId)
    conn_str = os.getenv('IOTHUB_DEVICE_CONNECTION_STRING', '') or os.getenv('IOTHUB_CONNECTION_STRING', '')
    IOTHUB_CONNECTION_STRING = conn_str.strip().strip('"').strip("'")
    
    if not IOTHUB_CONNECTION_STRING or 'DeviceId=' not in IOTHUB_CONNECTION_STRING:
        print("[IOTHUB] Invalid or missing connection string (must include DeviceId)")
        config_store['iothub_connected'] = False
        return False

    IOTHUB_AVAILABLE = True
    twin_update_callback = update_callback
    stop_twin_listener = False
    
    try:
        from azure.iot.device import IoTHubDeviceClient
        
        print(f"[IOTHUB] Connecting...")
        device_client = IoTHubDeviceClient.create_from_connection_string(
            IOTHUB_CONNECTION_STRING,
            keep_alive=60
        )
        
        device_client.on_twin_desired_properties_patch_received = on_twin_desired_properties_patch
        device_client.on_method_request_received = handle_direct_method
        
        device_client.connect()
        print(f"[IOTHUB] Connected successfully!")
        
        # Initial Sync
        _perform_initial_sync()
        
        config_store['iothub_connected'] = True
        
        # Start Background Sync Thread
        twin_listener_thread = threading.Thread(target=_sync_loop, daemon=True)
        twin_listener_thread.start()
        
        return True
        
    except Exception as e:
        print(f"[IOTHUB] Connection failed: {e}")
        config_store['iothub_connected'] = False
        return False

def _perform_initial_sync():
    """Read initial twin state and apply it."""
    try:
        twin = device_client.get_twin()
        desired = twin.get('desired', {})
        
        filtered_desired = {k: v for k, v in desired.items() if not k.startswith('$')}
        if filtered_desired:
            print(f"[IOTHUB] Initial desired properties: {filtered_desired}")
            on_twin_desired_properties_patch(filtered_desired, is_initial_sync=True)
            
        # Report initial state immediately (bypass buffer for startup)
        from .alarm_service import alarm_config
        initial_state = {
            'device_started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'alarm_enabled': alarm_config.get('enabled', False),
            'alarm_time': alarm_config.get('wake_time', '07:00'),
            'smart_wakeup_window': alarm_config.get('window_minutes', 30)
        }
        _send_reported_properties(initial_state)
        
    except Exception as e:
        print(f"[IOTHUB] Initial sync failed: {e}")

def on_twin_desired_properties_patch(patch, is_initial_sync=False):
    """Handle updates from Azure."""
    if not patch: return
    
    filtered_patch = {k: v for k, v in patch.items() if not k.startswith('$')}
    if not filtered_patch: return
    
    print(f"[IOTHUB] Received patch: {filtered_patch}")
    
    updates_to_report = {}
    
    # 1. Update Config Store (Idempotent)
    for key in ['cloud_enabled', 'monitoring_active']:
        if key in filtered_patch:
            if config_store.get(key) != filtered_patch[key]:
                config_store[key] = filtered_patch[key]
                updates_to_report[key] = filtered_patch[key]

    # 2. Update Alarm Config (Idempotent)
    if any(k in filtered_patch for k in ['alarm_time', 'smart_wakeup_window', 'capture_enabled', 'alarm_enabled']):
        try:
            from .alarm_service import alarm_config
            
            current_time = alarm_config.get('wake_time', '07:00')
            current_window = alarm_config.get('window_minutes', 30)
            current_enabled = alarm_config.get('enabled', False)
            
            new_time = filtered_patch.get('alarm_time', current_time)
            new_window = filtered_patch.get('smart_wakeup_window', current_window)
            
            # Handle enabled flag (Azure uses 'capture_enabled', we support 'alarm_enabled' too)
            new_enabled = current_enabled
            if 'capture_enabled' in filtered_patch:
                new_enabled = filtered_patch['capture_enabled']
            elif 'alarm_enabled' in filtered_patch:
                new_enabled = filtered_patch['alarm_enabled']
            
            # STRICT IDEMPOTENCY CHECK
            if (new_time != current_time or 
                new_window != current_window or 
                new_enabled != current_enabled):
                
                alarm_config['wake_time'] = new_time
                alarm_config['window_minutes'] = new_window
                alarm_config['enabled'] = new_enabled
                alarm_config['triggered'] = False
                
                print(f"[IOTHUB] Applied alarm update: {new_enabled}, {new_time}, {new_window}")
                
                updates_to_report['alarm_enabled'] = new_enabled
                updates_to_report['alarm_time'] = new_time
                updates_to_report['smart_wakeup_window'] = new_window
            else:
                print("[IOTHUB] Alarm update matches current state - ignoring")
                
        except Exception as e:
            print(f"[IOTHUB] Error applying alarm patch: {e}")
            
    if twin_update_callback:
        twin_update_callback(filtered_patch)

    # 3. Queue updates to reported properties (Outgoing Buffer)
    if updates_to_report:
        report_twin_properties(updates_to_report, skip_mqtt=True)

def report_twin_properties(properties, skip_mqtt=False):
    """
    Add properties to the Outgoing Buffer.
    Does NOT send immediately to Azure.
    """
    global _pending_report
    
    # MQTT is separate - can send immediately with its own rate limit
    if not skip_mqtt:
        _publish_mqtt_safe(properties)
        
    with _lock:
        _pending_report.update(properties)
        print(f"[IOTHUB] Buffered updates: {properties}")

def _sync_loop():
    """Background thread to flush the Outgoing Buffer."""
    global _pending_report, _circuit_breaker_tripped, _circuit_breaker_reset_time
    
    while not stop_twin_listener:
        time.sleep(10)  # Check every 10 seconds, but enforce 60s interval in logic
        
        if stop_twin_listener: break
        
        # Circuit Breaker Cooldown
        if _circuit_breaker_tripped:
            if time.time() > _circuit_breaker_reset_time:
                print("[IOTHUB] Circuit breaker cooldown expired. Resuming.")
                _circuit_breaker_tripped = False
            else:
                continue

        with _lock:
            if not _pending_report:
                continue
            to_send = _pending_report.copy()
            # Don't clear yet, wait for success
            
        # Check rate limit
        if time.time() - _last_report_time < _MIN_REPORT_INTERVAL:
            continue
            
        # Try to send
        if _send_reported_properties(to_send):
            with _lock:
                # Remove sent keys from buffer (in case new ones were added)
                for k in to_send:
                    if k in _pending_report and _pending_report[k] == to_send[k]:
                        del _pending_report[k]

def _send_reported_properties(properties):
    """Actual network call to Azure with Circuit Breaker."""
    global _last_report_time, _message_count, _message_count_window
    global _circuit_breaker_tripped, _circuit_breaker_reset_time
    
    if not device_client: return False
    
    current_time = time.time()
    
    # Circuit Breaker Logic
    if current_time - _message_count_window > 60:
        _message_count = 0
        _message_count_window = current_time
        
    if _message_count >= _MAX_MESSAGES_PER_MINUTE:
        print(f"[IOTHUB] CRITICAL: Message flood detected ({_message_count}/min). Tripping circuit breaker for {_CIRCUIT_BREAKER_COOLDOWN}s.")
        _circuit_breaker_tripped = True
        _circuit_breaker_reset_time = current_time + _CIRCUIT_BREAKER_COOLDOWN
        return False
        
    try:
        properties['last_sync'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        device_client.patch_twin_reported_properties(properties)
        
        _last_report_time = current_time
        _message_count += 1
        print(f"[IOTHUB] Successfully reported: {properties}")
        return True
    except Exception as e:
        print(f"[IOTHUB] Report failed: {e}")
        return False

def _publish_mqtt_safe(properties):
    """Publish to MQTT with rate limiting."""
    global _last_mqtt_publish_time
    current_time = time.time()
    if current_time - _last_mqtt_publish_time >= _MIN_MQTT_INTERVAL:
        try:
            from .mqtt_service import publish_twin_reported
            publish_twin_reported(properties)
            _last_mqtt_publish_time = current_time
        except Exception:
            pass

def handle_direct_method(request):
    from azure.iot.device import MethodResponse
    print(f"[IOTHUB] Direct method: {request.name}")
    
    method_name = request.name
    payload = request.payload
    
    response_payload = {"result": "unknown method"}
    status = 404
    
    if method_name == "getStatus":
        response_payload = {
            "fitbit_connected": config_store.get('fitbit_connected', False),
            "cloud_enabled": config_store.get('cloud_enabled', True),
            "monitoring_active": config_store.get('monitoring_active', False),
            "mqtt_connected": config_store.get('mqtt_connected', False),
            "pending_sync_count": config_store.get('pending_sync_count', 0)
        }
        status = 200
    
    elif method_name == "setCloudEnabled":
        enabled = payload.get('enabled', True) if isinstance(payload, dict) else True
        config_store['cloud_enabled'] = enabled
        response_payload = {"cloud_enabled": enabled}
        status = 200
    
    elif method_name == "triggerFetch":
        response_payload = {"message": "Fetch triggered"}
        status = 200
    
    elif method_name == "setAlarm":
        if isinstance(payload, dict):
            response_payload = {
                "wake_time": payload.get('wake_time', '07:00'),
                "window_minutes": payload.get('window_minutes', 30)
            }
            status = 200
        else:
            response_payload = {"error": "Invalid payload"}
            status = 400
    
    return MethodResponse.create_from_method_request(request, status, response_payload)

def send_telemetry(data):
    """Send telemetry message (separate from Twin)."""
    if not device_client: return False
    try:
        from azure.iot.device import Message
        msg = Message(json.dumps(data))
        msg.content_type = "application/json"
        msg.content_encoding = "utf-8"
        device_client.send_message(msg)
        return True
    except Exception as e:
        print(f"[IOTHUB] Telemetry failed: {e}")
        return False

def update_alarm_twin(enabled, wake_time=None, window_minutes=None):
    """Public API to update alarm twin."""
    props = {'alarm_enabled': enabled, 'capture_enabled': enabled}
    if wake_time: props['alarm_time'] = wake_time
    if window_minutes: props['smart_wakeup_window'] = window_minutes
    report_twin_properties(props)

def stop_iothub():
    global stop_twin_listener
    stop_twin_listener = True
    if device_client:
        try:
            device_client.shutdown()
        except: pass

def is_connected():
    return device_client is not None and config_store.get('iothub_connected', False)
