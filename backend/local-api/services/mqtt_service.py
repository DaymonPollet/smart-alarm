"""
MQTT Service - Publishes device state and twin updates to MQTT broker
Uses HiveMQ public broker (broker.hivemq.com) for easy connectivity
"""
import json
import threading
import time
import random
from datetime import datetime, timezone
from .config import (
    MQTT_BROKER, MQTT_PORT, 
    MQTT_TOPIC_PREDICTIONS, MQTT_TOPIC_ALERTS, 
    MQTT_TOPIC_TWIN, MQTT_TOPIC_CONFIG,
    config_store
)

try: 
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("[MQTT] paho-mqtt not installed. MQTT features disabled.")

mqtt_client = None
reconnect_thread = None
stop_reconnect = False
DEVICE_ID = "RPISmartHome"

def on_mqtt_connect(client, userdata, flags, rc):
    """Callback when client connects to broker"""
    if rc == 0:
        config_store['mqtt_connected'] = True
        print(f"[MQTT] Connected to {MQTT_BROKER} successfully!")
        # Subscribe to config changes (cloud -> device)
        client.subscribe(MQTT_TOPIC_CONFIG)
        client.subscribe(MQTT_TOPIC_ALERTS)
        print(f"[MQTT] Subscribed to: {MQTT_TOPIC_CONFIG}, {MQTT_TOPIC_ALERTS}")
        # Publish initial status
        publish_device_status()
    else:
        config_store['mqtt_connected'] = False
        error_messages = {
            1: "incorrect protocol version",
            2: "invalid client identifier", 
            3: "server unavailable",
            4: "bad username or password",
            5: "not authorized"
        }
        print(f"[MQTT] Connection failed: {error_messages.get(rc, f'unknown error {rc}')}")

def on_mqtt_disconnect(client, userdata, rc):
    config_store['mqtt_connected'] = False
    if rc != 0:
        print(f"[MQTT] Unexpected disconnect (rc={rc}), will retry...")

def on_mqtt_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[MQTT] Received on {msg.topic}: {payload}")
    except Exception as e:
        print(f"[MQTT] Message parse error: {e}")

def mqtt_reconnect_loop():
    global mqtt_client, stop_reconnect
    
    while not stop_reconnect:
        if mqtt_client and not config_store.get('mqtt_connected'):
            try:
                mqtt_client.reconnect()
            except Exception:
                pass
        time.sleep(10)

def init_mqtt():
    """Initialize MQTT client and connect to HiveMQ public broker"""
    global mqtt_client, reconnect_thread, stop_reconnect
    
    if not MQTT_AVAILABLE:
        print("[MQTT] Library not available")
        return False
    
    stop_reconnect = False
    
    try:
        # Use unique client ID to avoid conflicts on public broker
        client_id = f"{DEVICE_ID}_{random.randint(1000, 9999)}"
        mqtt_client = mqtt.Client(client_id=client_id, clean_session=True)
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_disconnect = on_mqtt_disconnect
        mqtt_client.on_message = on_mqtt_message
        
        mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)
        
        print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            mqtt_client.loop_start()
        except Exception as e:
            print(f"[MQTT] Initial connection failed: {e}")
            print("[MQTT] Will retry in background...")
            mqtt_client.loop_start()
        
        reconnect_thread = threading.Thread(target=mqtt_reconnect_loop, daemon=True)
        reconnect_thread.start()
        
        return True
    except Exception as e:
        print(f"[MQTT] Init error: {e}")
        return False

def stop_mqtt():
    global mqtt_client, stop_reconnect
    
    stop_reconnect = True
    
    if mqtt_client:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        except Exception:
            pass
    
    config_store['mqtt_connected'] = False

def publish_mqtt(topic, payload):
    if not mqtt_client:
        return False
    
    try:
        result = mqtt_client.publish(topic, json.dumps(payload), qos=1)
        return result.rc == 0
    except Exception as e:
        print(f"[MQTT] Publish error: {e}")
        return False

def publish_device_status():
    """Publish current device status to MQTT"""
    if not mqtt_client or not config_store.get('mqtt_connected'):
        return False
    
    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": DEVICE_ID,
        "type": "status",
        "data": {
            "fitbit_connected": config_store.get('fitbit_connected', False),
            "cloud_enabled": config_store.get('cloud_enabled', True),
            "monitoring_active": config_store.get('monitoring_active', False),
            "iothub_connected": config_store.get('iothub_connected', False),
            "pending_sync_count": config_store.get('pending_sync_count', 0)
        }
    }
    return publish_mqtt(MQTT_TOPIC_TWIN, status)

def publish_twin_reported(properties):
    """
    Publish reported twin properties to MQTT.
    This mirrors what we report to Azure IoT Hub, making it visible via MQTT too.
    """
    if not mqtt_client or not config_store.get('mqtt_connected'):
        print(f"[MQTT] Cannot publish - connected: {config_store.get('mqtt_connected')}")
        return False
    
    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": DEVICE_ID,
        "type": "reported_properties",
        "properties": properties
    }
    result = publish_mqtt(MQTT_TOPIC_TWIN, message)
    print(f"[MQTT] Published reported properties: {properties} -> success={result}", flush=True)
    return result

def publish_alarm_update(enabled, wake_time=None, window_minutes=None):
    """Publish alarm configuration update to MQTT"""
    if not mqtt_client or not config_store.get('mqtt_connected'):
        return False
    
    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": DEVICE_ID,
        "type": "alarm_update",
        "data": {
            "alarm_enabled": enabled,
            "alarm_wake_time": wake_time,
            "alarm_window_minutes": window_minutes
        }
    }
    return publish_mqtt(MQTT_TOPIC_TWIN, message)

def publish_prediction(prediction_data):
    """Publish sleep prediction to MQTT"""
    if not mqtt_client or not config_store.get('mqtt_connected'):
        return False
    
    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": DEVICE_ID,
        "type": "prediction",
        "data": prediction_data
    }
    return publish_mqtt(MQTT_TOPIC_PREDICTIONS, message)

def get_mqtt_client():
    return mqtt_client

def is_mqtt_connected():
    return config_store.get('mqtt_connected', False)
