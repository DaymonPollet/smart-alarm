import json
from .config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_PREDICTIONS, MQTT_TOPIC_ALERTS, config_store

try: 
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("[MQTT] paho-mqtt not installed. MQTT features disabled.")

# NOTE: service is currently still offline
mqtt_client = None

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        config_store['mqtt_connected'] = True
        print("[MQTT] Connected to broker")
    else:
        config_store['mqtt_connected'] = False
        print(f"[MQTT] Connection failed with code {rc}")

def on_mqtt_disconnect(client, userdata, rc):
    config_store['mqtt_connected'] = False
    print("[MQTT] Disconnected from broker")

def init_mqtt():
    global mqtt_client
    
    if not MQTT_AVAILABLE:
        return
    
    try:
        mqtt_client = mqtt.Client(client_id="smart-alarm-api")
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_disconnect = on_mqtt_disconnect
        
        mqtt_client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"[MQTT] Init error: {e}")

def publish_mqtt(topic, payload):
    if not mqtt_client or not config_store.get('mqtt_connected'):
        return False
    
    try:
        result = mqtt_client.publish(topic, json.dumps(payload), qos=1)
        return result.rc == 0
    except Exception as e:
        print(f"[MQTT] Publish error: {e}")
        return False

def get_mqtt_client():
    return mqtt_client
