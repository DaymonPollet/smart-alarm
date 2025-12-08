import os
import time
import json
import logging
import threading
from pathlib import Path
from dotenv import load_dotenv

from .actuator import SmartAlarmController
from .model import SleepStagePredictor
from .sensor import EnvironmentSensor
from .storage import LocalStorage
from .communication import IoTHubClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parents[2] / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

class SmartAlarmApp:
    def __init__(self):
        self.actuator = SmartAlarmController()
        self.model = SleepStagePredictor()
        self.sensor = EnvironmentSensor()
        self.storage = LocalStorage()
        
        conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
        if not conn_str:
            logger.warning("IOTHUB_DEVICE_CONNECTION_STRING not found in config/.env. Running in offline mode.")
        
        self.comm = IoTHubClient(
            conn_str, 
            message_callback=self.on_message_received,
            twin_callback=self.on_twin_patch_received
        )
        
        # default config, might remove some useless values later on
        self.config = {
            "alarm_time": "07:30",
            "smart_wakeup_window": 45,
            "sensor_interval": 60,
            "capture_enabled": True,
            "capture_interval": 10,
            "battery_level": 100
        }
        
        self.running = True

    def start(self):
        logger.info("Starting Smart Alarm App...")
        if self.comm.client: # connect only if client initialized
            self.comm.connect()
            # get connection
            twin = self.comm.get_twin()
            if twin and 'desired' in twin:
                self.update_config(twin['desired'])

        # start of sensor loop in new thread
        self.sensor_thread = threading.Thread(target=self.sensor_loop)
        self.sensor_thread.daemon = True
        self.sensor_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        logger.info("Stopping Smart Alarm App...")
        self.running = False
        self.actuator.cleanup()
        self.comm.shutdown()

    def sensor_loop(self):
        while self.running:
            if not self.config["capture_enabled"]:
                time.sleep(5)
                continue

            # 1. Read Sensor
            data = self.sensor.read_sensor_data()
            
            # 2. Store Locally
            self.storage.save_data(data)
            
            # 3. Send to Cloud
            self.comm.send_telemetry(data)
            
            time.sleep(self.config["sensor_interval"])

    def on_message_received(self, message):
        """Handle incoming messages (e.g. Fitbit data from Cloud)"""
        try:
            payload = message.data.decode("utf-8")
            data = json.loads(payload)
            logger.info(f"Received message: {data.get('data_type', 'unknown')}")
            
            if data.get('data_type') == 'sleep_metrics':
                # run local model
                analysis = self.model.analyze_sleep_data(data)
                logger.info(f"Sleep Analysis Result: {analysis}")
                
                # If 'optimal' wake time -> trigger alarm
                if analysis.get('should_wake_now'):
                    logger.info("Optimal wake time detected! Triggering alarm...")
                    self.actuator.trigger_alarm()
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def on_twin_patch_received(self, patch):
        """Handle configuration updates from Cloud"""
        logger.info(f"Received twin patch: {patch}")
        self.update_config(patch)
        
        # report back -> update config
        self.comm.update_reported_properties(self.config)

    def update_config(self, config_data):
        # Map Device Twin properties to local config
        keys = ["alarm_time", "smart_wakeup_window", "sensor_interval", "capture_enabled", "capture_interval"]
        for key in keys:
            if key in config_data:
                self.config[key] = config_data[key]
        
        logger.info(f"Configuration updated: {self.config}")

if __name__ == "__main__":
    app = SmartAlarmApp()
    app.start()
