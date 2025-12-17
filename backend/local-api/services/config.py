import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(env_path)

def get_env(key, default=''):
    """Get env var, stripping quotes if present."""
    val = os.getenv(key, default)
    if val and val.startswith('"') and val.endswith('"'):
        val = val[1:-1]
    if val and val.startswith("'") and val.endswith("'"):
        val = val[1:-1]
    return val

FITBIT_API_BASE = 'https://api.fitbit.com'
FITBIT_CLIENT_ID = get_env('FITBIT_CLIENT_ID')
FITBIT_CLIENT_SECRET = get_env('FITBIT_CLIENT_SECRET')
FITBIT_REDIRECT_URI = get_env('FITBIT_REDIRECT_URI', 'http://127.0.0.1:8080')

FITBIT_ACCESS_TOKEN = get_env('FITBIT_ACCESS_TOKEN')
FITBIT_REFRESH_TOKEN = get_env('FITBIT_REFRESH_TOKEN')

AZURE_ENDPOINT_URL = get_env('AZURE_ENDPOINT_URL')
AZURE_ENDPOINT_KEY = get_env('AZURE_ENDPOINT_KEY')
AZURE_STORAGE_CONNECTION_STRING = get_env('AZURE_STORAGE_CONNECTION_STRING')
AZURE_STORAGE_CONTAINER = get_env('AZURE_STORAGE_CONTAINER', 'smart-alarm-data')

APPINSIGHTS_CONNECTION_STRING = get_env('APPINSIGHTS_CONNECTION_STRING')

# Use HiveMQ public broker by default (like lab exercises)
MQTT_BROKER = get_env('MQTT_BROKER', 'broker.hivemq.com')
MQTT_PORT = int(get_env('MQTT_PORT', '1883'))
MQTT_TOPIC_BASE = get_env('MQTT_TOPIC_BASE', 'howest/smartalarm')
MQTT_TOPIC_PREDICTIONS = f"{MQTT_TOPIC_BASE}/predictions"
MQTT_TOPIC_ALERTS = f"{MQTT_TOPIC_BASE}/alerts"
MQTT_TOPIC_TWIN = f"{MQTT_TOPIC_BASE}/twin"
MQTT_TOPIC_CONFIG = f"{MQTT_TOPIC_BASE}/config"

DB_PATH = get_env('DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'sleep_data.db'))
MODEL_DIR = get_env('MODEL_PATH', os.path.join(os.path.dirname(__file__), '..', '..', '..', 'local_model'))

data_store = []
config_store = {
    'fitbit_connected': bool(FITBIT_ACCESS_TOKEN and FITBIT_ACCESS_TOKEN != ''),
    'monitoring_active': False,
    'azure_available': bool(AZURE_ENDPOINT_URL),
    'cloud_enabled': True,
    'mqtt_connected': False,
    'insights_connected': False,
    'pending_sync_count': 0
}

lag_features = {
    'Score_Lag1': None,
    'DeepSleep_Lag1': None,
    'RHR_Lag1': None
}
