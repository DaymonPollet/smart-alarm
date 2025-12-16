import json
import threading
import time
from .config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_PREDICTIONS, MQTT_TOPIC_ALERTS, config_store

try: 
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("[MQTT] paho-mqtt not installed. MQTT features disabled.")

mqtt_client = None
reconnect_thread = None
stop_reconnect = False

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        config_store['mqtt_connected'] = True
        print("[MQTT] Connected to broker")
        client.subscribe(MQTT_TOPIC_ALERTS)
    else:
        config_store['mqtt_connected'] = False
        print(f"[MQTT] Connection failed with code {rc}")

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
    global mqtt_client, reconnect_thread, stop_reconnect
    
    if not MQTT_AVAILABLE:
        print("[MQTT] Library not available")
        return False
    
    stop_reconnect = False
    
    try:
        mqtt_client = mqtt.Client(client_id="smart-alarm-api", clean_session=True)
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_disconnect = on_mqtt_disconnect
        mqtt_client.on_message = on_mqtt_message
        
        mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)
        
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            mqtt_client.loop_start()
            print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT}")
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

def get_mqtt_client():
    return mqtt_client
