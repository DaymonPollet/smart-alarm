"""
Azure IoT Hub Device Twin Service
Handles bidirectional configuration sync between the edge device and Azure cloud.
"""
import json
import threading
import time
import logging
import sys
from .config import config_store

# Suppress noisy Azure IoT device logging
logging.getLogger('azure.iot.device').setLevel(logging.CRITICAL)
logging.getLogger('azure.iot.device.common').setLevel(logging.CRITICAL)
logging.getLogger('azure.iot.device.iothub').setLevel(logging.CRITICAL)

# Suppress background thread exceptions printed by Azure SDK
_original_excepthook = sys.excepthook
def _suppressed_excepthook(exc_type, exc_value, exc_tb):
    # Suppress ConnectionDroppedError spam from Azure SDK
    exc_name = getattr(exc_type, '__name__', str(exc_type))
    if 'ConnectionDroppedError' in exc_name or 'ConnectionDroppedError' in str(exc_value):
        return  # Silently ignore
    _original_excepthook(exc_type, exc_value, exc_tb)
sys.excepthook = _suppressed_excepthook

# Also suppress unraisable exceptions in background threads (Python 3.8+)
def _suppressed_unraisablehook(unraisable):
    exc_name = getattr(unraisable.exc_type, '__name__', str(unraisable.exc_type))
    if 'ConnectionDroppedError' in exc_name or 'ConnectionDroppedError' in str(unraisable.exc_value):
        return  # Silently ignore
    sys.__unraisablehook__(unraisable)

if hasattr(sys, 'unraisablehook'):
    sys.unraisablehook = _suppressed_unraisablehook

# Suppress threading excepthook for background threads (Python 3.8+)
def _suppressed_threading_excepthook(args):
    exc_name = getattr(args.exc_type, '__name__', str(args.exc_type))
    if 'ConnectionDroppedError' in exc_name or 'ConnectionDroppedError' in str(args.exc_value):
        return  # Silently ignore
    # Fall back to default behavior
    sys.__excepthook__(args.exc_type, args.exc_value, args.exc_traceback)

if hasattr(threading, 'excepthook'):
    threading.excepthook = _suppressed_threading_excepthook

IOTHUB_CONNECTION_STRING = None
IOTHUB_AVAILABLE = False

try:
    from azure.iot.device import IoTHubDeviceClient, MethodResponse
    import os
    from dotenv import load_dotenv
    load_dotenv()
    conn_str = os.getenv('IOTHUB_CONNECTION_STRING', '')
    # Strip any surrounding quotes that might come from .env file
    IOTHUB_CONNECTION_STRING = conn_str.strip().strip('"').strip("'")
    if IOTHUB_CONNECTION_STRING and 'HostName=' in IOTHUB_CONNECTION_STRING:
        IOTHUB_AVAILABLE = True
        print(f"[IOTHUB] Connection string loaded (DeviceId in string: {'DeviceId=' in IOTHUB_CONNECTION_STRING})")
    else:
        print(f"[IOTHUB] Invalid or missing connection string")
except ImportError:
    print("[IOTHUB] azure-iot-device not installed. IoT Hub features disabled.")

device_client = None
twin_update_callback = None
stop_twin_listener = False
twin_listener_thread = None

# Rate limiting for IoT Hub operations (free tier: 8000 messages/day = ~5.5/min)
_last_report_time = 0
_MIN_REPORT_INTERVAL = 60  # Minimum 60 seconds between twin reports (max 1440/day)
_pending_report = None  # Queue up properties if rate limited
_reporting_from_callback = False  # Prevent callback loops
_last_mqtt_publish_time = 0
_MIN_MQTT_INTERVAL = 5  # Minimum 5 seconds between MQTT twin publishes
_initial_sync_done = False  # Track if initial sync completed

def get_default_twin_properties():
    return {
        'cloud_enabled': config_store.get('cloud_enabled', True),
        'monitoring_active': config_store.get('monitoring_active', False),
        'alarm_enabled': False,
        'alarm_wake_time': '07:00',
        'alarm_window_minutes': 30,
        'fetch_interval_seconds': 90,
        'last_updated': None
    }

def on_twin_desired_properties_patch(patch, is_initial_sync=False):
    """
    Callback when desired properties are updated from Azure portal/cloud.
    Applies changes locally and reports back to confirm.
    """
    global _reporting_from_callback, _initial_sync_done
    
    # Ignore empty patches or patches we just reported (prevent loops)
    if not patch or _reporting_from_callback:
        return
    
    # Filter out metadata keys
    filtered_patch = {k: v for k, v in patch.items() if not k.startswith('$')}
    if not filtered_patch:
        return
    
    print(f"[IOTHUB] Received twin patch: {filtered_patch}")
    
    reported = {}
    alarm_changed = False
    alarm_time = None
    alarm_window = None
    
    if 'cloud_enabled' in filtered_patch:
        config_store['cloud_enabled'] = filtered_patch['cloud_enabled']
        reported['cloud_enabled'] = filtered_patch['cloud_enabled']
        
    if 'monitoring_active' in filtered_patch:
        config_store['monitoring_active'] = filtered_patch['monitoring_active']
        reported['monitoring_active'] = filtered_patch['monitoring_active']
    
    if 'alarm_time' in filtered_patch:
        alarm_time = filtered_patch['alarm_time']
        reported['alarm_wake_time'] = alarm_time
        reported['alarm_enabled'] = True
        alarm_changed = True
        
    if 'smart_wakeup_window' in filtered_patch:
        alarm_window = filtered_patch['smart_wakeup_window']
        reported['alarm_window_minutes'] = alarm_window
        alarm_changed = True
    
    if 'alarm_enabled' in filtered_patch:
        reported['alarm_enabled'] = filtered_patch['alarm_enabled']
        if not filtered_patch['alarm_enabled']:
            alarm_changed = True
            alarm_time = None
    
    # Apply alarm changes locally (but don't trigger twin update from alarm_service)
    if alarm_changed:
        try:
            from .alarm_service import set_alarm, disable_alarm, alarm_config
            if alarm_time:
                # Set alarm without triggering twin update (we'll report below)
                alarm_config['enabled'] = True
                alarm_config['wake_time'] = alarm_time
                alarm_config['window_minutes'] = alarm_window or 30
                alarm_config['triggered'] = False
                print(f"[IOTHUB] Alarm configured from twin: {alarm_time}, window: {alarm_window or 30}")
            elif 'alarm_enabled' in filtered_patch and not filtered_patch['alarm_enabled']:
                alarm_config['enabled'] = False
                alarm_config['triggered'] = False
                print(f"[IOTHUB] Alarm disabled from twin")
        except Exception as e:
            print(f"[IOTHUB] Failed to apply alarm from twin: {e}")
    
    if twin_update_callback:
        twin_update_callback(filtered_patch)
    
    # Only report if we have something meaningful to report
    # Skip reporting on initial sync to avoid spam (we'll do one consolidated report)
    if reported and not is_initial_sync:
        reported['last_sync'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        _reporting_from_callback = True
        try:
            report_twin_properties(reported, skip_mqtt=True)  # Skip MQTT to reduce spam
        finally:
            _reporting_from_callback = False
    
    _initial_sync_done = True

def handle_direct_method(request):
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

def init_iothub(update_callback=None):
    """
    Initialize IoT Hub connection with Device Twin bidirectional sync.
    """
    global device_client, twin_update_callback, twin_listener_thread, stop_twin_listener
    
    if not IOTHUB_AVAILABLE or not IOTHUB_CONNECTION_STRING:
        print("[IOTHUB] Not configured or unavailable")
        config_store['iothub_connected'] = False
        return False
    
    twin_update_callback = update_callback
    stop_twin_listener = False
    
    try:
        print(f"[IOTHUB] Attempting connection...")
        device_client = IoTHubDeviceClient.create_from_connection_string(IOTHUB_CONNECTION_STRING)
        device_client.connect()
        print(f"[IOTHUB] Connected successfully!")
        
        device_client.on_twin_desired_properties_patch_received = on_twin_desired_properties_patch
        device_client.on_method_request_received = handle_direct_method
        
        try:
            twin = device_client.get_twin()
            print(f"[IOTHUB] Got device twin")
            desired = twin.get('desired', {})
            if desired:
                filtered = {k: v for k, v in desired.items() if not k.startswith('$')}
                if filtered:
                    print(f"[IOTHUB] Applying desired properties (initial sync): {filtered}")
                    on_twin_desired_properties_patch(filtered, is_initial_sync=True)
                    
                    # Do ONE consolidated report after initial sync
                    initial_reported = {
                        'device_started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        'last_sync': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    }
                    report_twin_properties(initial_reported, skip_mqtt=True)
        except Exception as e:
            print(f"[IOTHUB] Twin read failed: {e} - continuing without initial sync")
        
        config_store['iothub_connected'] = True
        print(f"[IOTHUB] Connected with Device Twin sync enabled")
        return True
        
    except Exception as e:
        import traceback
        print(f"[IOTHUB] Connection failed: {e}")
        config_store['iothub_connected'] = False
        return False

def report_twin_properties(properties, skip_mqtt=False):
    \"\"\"
    Report properties to IoT Hub Device Twin and optionally MQTT.
    Rate limited to prevent exceeding daily quota (8000 messages/day for free tier).
    
    Args:
        properties: Dict of properties to report
        skip_mqtt: If True, skip MQTT publish (use when called from twin callback to avoid spam)
    \"\"\"
    global _last_report_time, _pending_report, _last_mqtt_publish_time
    
    iothub_success = False
    mqtt_success = False
    
    # Optionally publish to MQTT with rate limiting
    if not skip_mqtt:
        current_mqtt_time = time.time()
        if current_mqtt_time - _last_mqtt_publish_time >= _MIN_MQTT_INTERVAL:
            try:
                from .mqtt_service import publish_twin_reported
                mqtt_success = publish_twin_reported(properties)
                _last_mqtt_publish_time = current_mqtt_time
            except Exception as e:
                print(f\"[MQTT] Twin publish failed: {e}\")
        else:
            print(f\"[MQTT] Rate limited - skipping twin publish\")
    
    # Rate limit IoT Hub operations
    current_time = time.time()
    time_since_last = current_time - _last_report_time
    
    if time_since_last < _MIN_REPORT_INTERVAL:
        # Queue this report, will be sent when rate limit expires
        if _pending_report:
            _pending_report.update(properties)  # Merge with existing pending
        else:
            _pending_report = properties.copy()
        print(f\"[IOTHUB] Rate limited - queued properties (next in {_MIN_REPORT_INTERVAL - time_since_last:.0f}s)\")
        return mqtt_success  # Return MQTT success status
    
    # Send to IoT Hub
    if device_client:
        try:
            # Merge any pending properties
            to_send = properties.copy()
            if _pending_report:
                to_send.update(_pending_report)
                _pending_report = None
            
            device_client.patch_twin_reported_properties(to_send)
            _last_report_time = current_time
            iothub_success = True
            print(f\"[IOTHUB] Reported twin properties: {to_send}\")
        except Exception as e:
            print(f"[IOTHUB] Twin report failed: {e}")
    
    return iothub_success or mqtt_success

def send_telemetry(data):
    if not device_client:
        return False
    
    try:
        from azure.iot.device import Message
        message = Message(json.dumps(data))
        message.content_type = "application/json"
        message.content_encoding = "utf-8"
        device_client.send_message(message)
        return True
    except Exception as e:
        print(f"[IOTHUB] Telemetry send failed: {e}")
        return False

def update_alarm_twin(enabled, wake_time=None, window_minutes=None):
    \"\"\"
    Update alarm settings in IoT Hub reported properties.
    MQTT publishing is handled by report_twin_properties (avoid duplicate publishes).
    \"\"\"
    properties = {
        'alarm_enabled': enabled,
        'last_sync': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }
    if wake_time:
        properties['alarm_wake_time'] = wake_time
    if window_minutes:
        properties['alarm_window_minutes'] = window_minutes
    
    # Report to IoT Hub and MQTT (report_twin_properties handles both)
    return report_twin_properties(properties)

def stop_iothub():
    global device_client, stop_twin_listener
    
    stop_twin_listener = True
    
    if device_client:
        try:
            device_client.shutdown()
        except Exception:
            pass
    
    config_store['iothub_connected'] = False

def get_device_client():
    return device_client

def is_connected():
    return device_client is not None and config_store.get('iothub_connected', False)

def test_iothub_operations():
    """
    Test IoT Hub operations and return diagnostic info.
    DISABLED to preserve daily message quota (8000/day on free tier).
    """
    return {
        'connection_string_loaded': bool(IOTHUB_CONNECTION_STRING),
        'has_device_id': 'DeviceId=' in (IOTHUB_CONNECTION_STRING or ''),
        'client_created': device_client is not None,
        'connected': is_connected(),
        'note': 'Test operations disabled to preserve message quota',
        'rate_limit': f'{_MIN_REPORT_INTERVAL}s between twin reports'
    }
