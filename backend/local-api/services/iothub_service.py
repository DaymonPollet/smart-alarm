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
    # Use DEVICE connection string (has DeviceId), not service connection string
    conn_str = os.getenv('IOTHUB_DEVICE_CONNECTION_STRING', '') or os.getenv('IOTHUB_CONNECTION_STRING', '')
    # Strip any surrounding quotes that might come from .env file
    IOTHUB_CONNECTION_STRING = conn_str.strip().strip('"').strip("'")
    if IOTHUB_CONNECTION_STRING and 'HostName=' in IOTHUB_CONNECTION_STRING and 'DeviceId=' in IOTHUB_CONNECTION_STRING:
        IOTHUB_AVAILABLE = True
        print(f"[IOTHUB] Device connection string loaded (DeviceId in string: True)")
    else:
        print(f"[IOTHUB] Invalid connection string - must be a DEVICE connection string with DeviceId")
except ImportError:
    print("[IOTHUB] azure-iot-device not installed. IoT Hub features disabled.")

device_client = None
twin_update_callback = None
stop_twin_listener = False
twin_listener_thread = None

# Rate limiting for IoT Hub operations (free tier: 8000 messages/day = ~5.5/min)
_last_report_time = 0
_MIN_REPORT_INTERVAL = 20  # 20 seconds = 3 per minute (max 4320/day, under 8000 limit)
_pending_report = None  # Queue up properties if rate limited
_reporting_from_callback = False  # Prevent callback loops
_last_mqtt_publish_time = 0
_MIN_MQTT_INTERVAL = 5  # Minimum 5 seconds between MQTT twin publishes
_initial_sync_done = False  # Track if initial sync completed
_pending_flush_timer = None  # Timer to flush pending reports

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
    
    Azure Twin property names:
    - alarm_time: "7:00" format
    - smart_wakeup_window: minutes (int)
    - capture_enabled: bool (maps to alarm_enabled)
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
    alarm_enabled = None
    
    # Handle cloud_enabled
    if 'cloud_enabled' in filtered_patch:
        config_store['cloud_enabled'] = filtered_patch['cloud_enabled']
        reported['cloud_enabled'] = filtered_patch['cloud_enabled']
        
    # Handle monitoring_active  
    if 'monitoring_active' in filtered_patch:
        config_store['monitoring_active'] = filtered_patch['monitoring_active']
        reported['monitoring_active'] = filtered_patch['monitoring_active']
    
    # Handle alarm_time (from Azure twin)
    if 'alarm_time' in filtered_patch:
        alarm_time = filtered_patch['alarm_time']
        alarm_changed = True
        
    # Handle smart_wakeup_window (from Azure twin)
    if 'smart_wakeup_window' in filtered_patch:
        alarm_window = filtered_patch['smart_wakeup_window']
        alarm_changed = True
    
    # Handle capture_enabled (Azure uses this for alarm on/off)
    if 'capture_enabled' in filtered_patch:
        alarm_enabled = filtered_patch['capture_enabled']
        alarm_changed = True
    
    # Also support alarm_enabled directly
    if 'alarm_enabled' in filtered_patch:
        alarm_enabled = filtered_patch['alarm_enabled']
        alarm_changed = True
    
    # Apply alarm changes locally
    if alarm_changed:
        try:
            from .alarm_service import alarm_config
            
            # Get current values for defaults
            current_time = alarm_config.get('wake_time', '07:00')
            current_window = alarm_config.get('window_minutes', 30)
            current_enabled = alarm_config.get('enabled', False)
            
            # Apply updates
            new_time = alarm_time if alarm_time else current_time
            new_window = alarm_window if alarm_window else current_window
            new_enabled = alarm_enabled if alarm_enabled is not None else (True if alarm_time else current_enabled)
            
            alarm_config['wake_time'] = new_time
            alarm_config['window_minutes'] = new_window
            alarm_config['enabled'] = new_enabled
            alarm_config['triggered'] = False
            
            print(f"[IOTHUB] Alarm updated from twin: enabled={new_enabled}, time={new_time}, window={new_window}")
            
            # Report back with our property names
            reported['alarm_enabled'] = new_enabled
            reported['alarm_time'] = new_time
            reported['smart_wakeup_window'] = new_window
            
        except Exception as e:
            print(f"[IOTHUB] Failed to apply alarm from twin: {e}")
    
    if twin_update_callback:
        twin_update_callback(filtered_patch)
    
    # Report back to confirm sync (unless initial sync)
    if reported and not is_initial_sync:
        reported['last_sync'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        _reporting_from_callback = True
        try:
            report_twin_properties(reported, skip_mqtt=True)
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
        print(f"[IOTHUB] Connection string device: {IOTHUB_CONNECTION_STRING.split('DeviceId=')[1].split(';')[0] if 'DeviceId=' in IOTHUB_CONNECTION_STRING else 'unknown'}")
        
        device_client = IoTHubDeviceClient.create_from_connection_string(
            IOTHUB_CONNECTION_STRING,
            keep_alive=60  # Keep connection alive
        )
        
        # Set up handlers BEFORE connecting
        device_client.on_twin_desired_properties_patch_received = on_twin_desired_properties_patch
        device_client.on_method_request_received = handle_direct_method
        
        device_client.connect()
        print(f"[IOTHUB] Connected successfully!")
        
        # Get initial twin state
        try:
            twin = device_client.get_twin()
            print(f"[IOTHUB] Got device twin")
            desired = twin.get('desired', {})
            reported = twin.get('reported', {})
            
            print(f"[IOTHUB] Current desired: {dict((k,v) for k,v in desired.items() if not k.startswith('$'))}")
            print(f"[IOTHUB] Current reported: {dict((k,v) for k,v in reported.items() if not k.startswith('$'))}")
            
            if desired:
                filtered = {k: v for k, v in desired.items() if not k.startswith('$')}
                if filtered:
                    print(f"[IOTHUB] Applying desired properties (initial sync): {filtered}")
                    on_twin_desired_properties_patch(filtered, is_initial_sync=True)
                    
                    # Report initial state to Azure
                    from .alarm_service import alarm_config
                    initial_reported = {
                        'device_started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        'last_sync': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        'alarm_enabled': alarm_config.get('enabled', False),
                        'alarm_time': alarm_config.get('wake_time', '07:00'),
                        'smart_wakeup_window': alarm_config.get('window_minutes', 30),
                        'capture_enabled': alarm_config.get('enabled', False)
                    }
                    print(f"[IOTHUB] Reporting initial state: {initial_reported}")
                    _do_report_twin(initial_reported)
        except Exception as e:
            print(f"[IOTHUB] Twin read failed: {e}")
            import traceback
            traceback.print_exc()
        
        config_store['iothub_connected'] = True
        print(f"[IOTHUB] Connected with Device Twin sync enabled")
        
        twin_listener_thread = threading.Thread(target=_keepalive_loop, daemon=True)
        twin_listener_thread.start()
        
        return True
        
    except Exception as e:
        import traceback
        print(f"[IOTHUB] Connection failed: {e}")
        traceback.print_exc()
        config_store['iothub_connected'] = False
        return False


def _do_report_twin(properties):
    """Internal function to report twin without rate limiting (for initial sync)."""
    global _last_report_time
    if device_client:
        try:
            device_client.patch_twin_reported_properties(properties)
            _last_report_time = time.time()
            print(f"[IOTHUB] Reported: {properties}")
            return True
        except Exception as e:
            print(f"[IOTHUB] Report failed: {e}")
            import traceback
            traceback.print_exc()
    return False


def _keepalive_loop():
    """Background thread to flush pending reports only."""
    global _pending_report, _last_report_time, stop_twin_listener
    
    while not stop_twin_listener:
        try:
            time.sleep(60)
            
            if stop_twin_listener:
                break
            
            if device_client and _pending_report:
                current_time = time.time()
                if current_time - _last_report_time >= _MIN_REPORT_INTERVAL:
                    to_send = _pending_report.copy()
                    _pending_report = None
                    try:
                        device_client.patch_twin_reported_properties(to_send)
                        _last_report_time = current_time
                    except Exception:
                        _pending_report = to_send
                        
        except Exception:
            pass

def report_twin_properties(properties, skip_mqtt=False):
    """
    Report properties to IoT Hub Device Twin and optionally MQTT.
    Rate limited to prevent exceeding daily quota (8000 messages/day for free tier).
    
    Args:
        properties: Dict of properties to report
        skip_mqtt: If True, skip MQTT publish (use when called from twin callback to avoid spam)
    """
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
                print(f"[MQTT] Twin publish failed: {e}\n")
        else:
            print(f"[MQTT] Rate limited - skipping twin publish\n")
    
    # Rate limit IoT Hub operations
    current_time = time.time()
    time_since_last = current_time - _last_report_time
    
    if time_since_last < _MIN_REPORT_INTERVAL:
        # Queue this report, will be sent when rate limit expires
        if _pending_report:
            _pending_report.update(properties)  # Merge with existing pending
        else:
            _pending_report = properties.copy()
        print(f"[IOTHUB] Rate limited - queued properties (next in {_MIN_REPORT_INTERVAL - time_since_last:.0f}s)\n")
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
            print(f"[IOTHUB] Reported twin properties: {to_send}\n")
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
    """
    Update alarm settings in IoT Hub reported properties.
    Uses property names that match Azure twin (alarm_time, smart_wakeup_window).
    """
    properties = {
        'alarm_enabled': enabled,
        'capture_enabled': enabled,  # Azure uses this name
        'last_sync': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }
    if wake_time:
        properties['alarm_time'] = wake_time  # Match Azure twin property name
    if window_minutes:
        properties['smart_wakeup_window'] = window_minutes  # Match Azure twin property name
    
    print(f"[IOTHUB] Updating alarm twin: enabled={enabled}, time={wake_time}, window={window_minutes}")
    
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
        'client_connected_property': device_client.connected if device_client else False,
        'note': 'Test operations disabled to preserve message quota',
        'rate_limit': f'{_MIN_REPORT_INTERVAL}s between twin reports'
    }


def get_twin_state():
    """Get current device twin state from IoT Hub."""
    if not device_client:
        return {'error': 'Client not connected'}
    
    try:
        twin = device_client.get_twin()
        return {
            'success': True,
            'desired': {k: v for k, v in twin.get('desired', {}).items() if not k.startswith('$')},
            'reported': {k: v for k, v in twin.get('reported', {}).items() if not k.startswith('$')},
            'desired_version': twin.get('desired', {}).get('$version'),
            'reported_version': twin.get('reported', {}).get('$version')
        }
    except Exception as e:
        return {'error': str(e)}


def force_report_state():
    """Force report current state to twin (bypass rate limit)."""
    if not device_client:
        return {'error': 'Client not connected'}
    
    try:
        from .alarm_service import alarm_config
        state = {
            'force_sync': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'alarm_enabled': alarm_config.get('enabled', False),
            'alarm_time': alarm_config.get('wake_time', '07:00'),
            'smart_wakeup_window': alarm_config.get('window_minutes', 30),
            'capture_enabled': alarm_config.get('enabled', False)
        }
        
        success = _do_report_twin(state)
        return {'success': success, 'reported': state}
    except Exception as e:
        return {'error': str(e)}
