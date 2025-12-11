import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LocalStorage:
    """
    Handles local storage of sensor data on the Raspberry Pi.
    Uses a JSON file for simplicity.
    """
    
    def __init__(self, storage_file='sensor_data.json'):
        self.storage_file = storage_file
        self._ensure_file_exists()
        
    def _ensure_file_exists(self):
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w') as f:
                json.dump([], f)
                
    def save_data(self, data):
        """
        Save a data record to local storage.
        """
        try:
            with open(self.storage_file, 'r') as f:
                current_data = json.load(f)
            
            current_data.append(data)
            
            # keep only last 1000 records to prevent file from growing too large
            if len(current_data) > 1000:
                current_data = current_data[-1000:]
                
            with open(self.storage_file, 'w') as f:
                json.dump(current_data, f, indent=2)
                
            logger.info("Data saved to local storage")
        except Exception as e:
            logger.error(f"Error saving data to local storage: {e}")

    def get_recent_data(self, limit=10):
        """
        Retrieve recent data records.
        """
        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
            return data[-limit:]
        except Exception as e:
            logger.error(f"Error reading local storage: {e}")
            return []
