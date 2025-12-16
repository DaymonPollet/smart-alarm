import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

FITBIT_API_BASE = 'https://api.fitbit.com'
FITBIT_CLIENT_ID = os.getenv('FITBIT_CLIENT_ID', '')
FITBIT_CLIENT_SECRET = os.getenv('FITBIT_CLIENT_SECRET', '')
FITBIT_REDIRECT_URI = os.getenv('FITBIT_REDIRECT_URI', 'http://127.0.0.1:8080')

FITBIT_ACCESS_TOKEN = os.getenv('FITBIT_ACCESS_TOKEN', '')
FITBIT_REFRESH_TOKEN = os.getenv('FITBIT_REFRESH_TOKEN', '')

AZURE_ENDPOINT_URL = os.getenv('AZURE_ENDPOINT_URL', '')
AZURE_ENDPOINT_KEY = os.getenv('AZURE_ENDPOINT_KEY', '')

MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_TOPIC_PREDICTIONS = os.getenv('MQTT_TOPIC_PREDICTIONS', 'smart-alarm/predictions')
MQTT_TOPIC_ALERTS = os.getenv('MQTT_TOPIC_ALERTS', 'smart-alarm/alerts')

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'sleep_data.db')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'local_model')

data_store = []
config_store = {
    'fitbit_connected': bool(FITBIT_ACCESS_TOKEN and FITBIT_ACCESS_TOKEN != ''),
    'monitoring_active': False,
    'azure_available': bool(AZURE_ENDPOINT_URL),
    'mqtt_connected': False
}

lag_features = {
    'Score_Lag1': None,
    'DeepSleep_Lag1': None,
    'RHR_Lag1': None
}
