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

def on_twin_desired_properties_patch(patch):
    """
    Callback when desired properties are updated from Azure portal/cloud.
    Applies changes locally and reports back to confirm.
    """
    print(f"[IOTHUB] Received twin patch: {patch}")
    
    reported = {}
    alarm_changed = False
    alarm_time = None
    alarm_window = None
    
    if 'cloud_enabled' in patch:
        config_store['cloud_enabled'] = patch['cloud_enabled']
        reported['cloud_enabled'] = patch['cloud_enabled']
        
    if 'monitoring_active' in patch:
        config_store['monitoring_active'] = patch['monitoring_active']
        reported['monitoring_active'] = patch['monitoring_active']
    
    if 'alarm_time' in patch:
        alarm_time = patch['alarm_time']
        reported['alarm_wake_time'] = alarm_time
        reported['alarm_enabled'] = True
        alarm_changed = True
        
    if 'smart_wakeup_window' in patch:
        alarm_window = patch['smart_wakeup_window']
        reported['alarm_window_minutes'] = alarm_window
        alarm_changed = True
    
    if 'alarm_enabled' in patch:
        reported['alarm_enabled'] = patch['alarm_enabled']
        if not patch['alarm_enabled']:
            alarm_changed = True
            alarm_time = None
    
    if alarm_changed:
        try:
            from .alarm_service import set_alarm, disable_alarm
            if alarm_time:
                set_alarm(alarm_time, alarm_window or 30)
                print(f"[IOTHUB] Alarm set from twin: {alarm_time}, window: {alarm_window or 30}")
            elif 'alarm_enabled' in patch and not patch['alarm_enabled']:
                disable_alarm()
                print(f"[IOTHUB] Alarm disabled from twin")
        except Exception as e:
            print(f"[IOTHUB] Failed to apply alarm from twin: {e}")
    
    if twin_update_callback:
        twin_update_callback(patch)
    
    reported['last_sync'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    report_twin_properties(reported)

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
                    print(f"[IOTHUB] Applying desired properties: {filtered}")
                    on_twin_desired_properties_patch(filtered)
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

def report_twin_properties(properties):
    """Report properties to IoT Hub Device Twin and MQTT"""
    iothub_success = False
    mqtt_success = False
    
    if device_client:
        try:
            device_client.patch_twin_reported_properties(properties)
            iothub_success = True
            print(f"[IOTHUB] Reported twin properties: {properties}")
        except Exception as e:
            print(f"[IOTHUB] Twin report failed: {e}")
    
    try:
        from .mqtt_service import publish_twin_reported
        mqtt_success = publish_twin_reported(properties)
    except Exception as e:
        print(f"[MQTT] Twin publish failed: {e}")
    
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
    """Update alarm settings in both IoT Hub reported properties and MQTT"""
    properties = {
        'alarm_enabled': enabled,
        'last_sync': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }
    if wake_time:
        properties['alarm_wake_time'] = wake_time
    if window_minutes:
        properties['alarm_window_minutes'] = window_minutes
    
    # Report to IoT Hub
    result = report_twin_properties(properties)
    
    # Also publish to MQTT
    try:
        from .mqtt_service import publish_alarm_update
        publish_alarm_update(enabled, wake_time, window_minutes)
    except Exception as e:
        print(f"[IOTHUB] Could not publish alarm to MQTT: {e}")
    
    return result

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
    Useful for debugging 403 permission errors.
    """
    results = {
        'connection_string_loaded': bool(IOTHUB_CONNECTION_STRING),
        'has_device_id': 'DeviceId=' in (IOTHUB_CONNECTION_STRING or ''),
        'client_created': device_client is not None,
        'get_twin': {'success': False, 'error': None},
        'report_properties': {'success': False, 'error': None},
        'send_telemetry': {'success': False, 'error': None}
    }
    
    if not device_client:
        results['error'] = 'No device client - not connected'
        return results
    
    # Test get_twin
    try:
        twin = device_client.get_twin()
        results['get_twin']['success'] = True
        results['get_twin']['desired_keys'] = list(twin.get('desired', {}).keys())
    except Exception as e:
        results['get_twin']['error'] = str(e)
    
    # Test report properties
    try:
        test_prop = {'test_ping': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        device_client.patch_twin_reported_properties(test_prop)
        results['report_properties']['success'] = True
    except Exception as e:
        results['report_properties']['error'] = str(e)
    
    # Test telemetry
    try:
        from azure.iot.device import Message
        msg = Message(json.dumps({'test': 'ping'}))
        msg.content_type = "application/json"
        device_client.send_message(msg)
        results['send_telemetry']['success'] = True
    except Exception as e:
        results['send_telemetry']['error'] = str(e)
    
    return results
