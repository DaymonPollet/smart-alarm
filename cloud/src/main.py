import os
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from .fitbit_client import FitbitClient
from .iot_hub_service import IoTHubService
from .data_processor import DataProcessor
from .cloud_ai import CloudSleepAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from config/.env
env_path = Path(__file__).resolve().parents[2] / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

class FitbitDataFerryApp:
    def __init__(self):
        self.fitbit = FitbitClient(
            os.getenv('FITBIT_CLIENT_ID'),
            os.getenv('FITBIT_CLIENT_SECRET'),
            os.getenv('FITBIT_ACCESS_TOKEN'),
            os.getenv('FITBIT_REFRESH_TOKEN')
        )
        
        self.iot_hub = IoTHubService(os.getenv('IOTHUB_CONNECTION_STRING'))
        self.processor = DataProcessor()
        self.cloud_ai = CloudSleepAnalyzer()
        self.target_device_id = os.getenv('TARGET_DEVICE_ID', 'rpi-smart-alarm')

    def run(self):
        logger.info("Starting Fitbit Data Ferry...")
        
        try:
            # 1. Fetch Data
            sleep_data = self.fitbit.fetch_sleep_data()
            hr_data = self.fitbit.fetch_heart_rate_intraday()
            hrv_data = self.fitbit.fetch_hrv_data()
            
            # 2. Run Cloud AI
            ai_result = self.cloud_ai.detect_anomalies(sleep_data)
            
            # 3. Process Data
            sleep_stages = self.processor.process_sleep_stages(sleep_data)
            
            if not sleep_stages:
                logger.warning("No sleep data found.")
                return

            # 4. Combine Data (include AI result)
            payload = self.processor.combine_data(sleep_stages, hr_data, hrv_data, self.target_device_id)
            payload['cloud_analysis'] = ai_result
            
            # 5. Send to Device
            self.iot_hub.send_c2d_message(self.target_device_id, payload)
            
        except Exception as e:
            logger.error(f"Error in Data Ferry pipeline: {e}")

if __name__ == "__main__":
    app = FitbitDataFerryApp()
    app.run()
