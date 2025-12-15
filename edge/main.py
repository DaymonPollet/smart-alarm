import os
import time
import numpy as np
from datetime import datetime, time as dt_time
from dotenv import load_dotenv
from fitbit_service import FitbitService
from storage_service import StorageService
from azure_service import AzureService
from model_service import ModelService

load_dotenv()

class SmartAlarmEdge:
    def __init__(self):
        self.fitbit = FitbitService()
        self.storage = StorageService()
        self.azure = AzureService()
        self.local_model = ModelService(is_cloud=False)
        self.cloud_model = ModelService(is_cloud=True)
        self.enabled = os.getenv('ENABLE_FITBIT_API', 'false').lower() == 'true'
        
        self.azure.connect()
    
    def is_night_time(self):
        now = datetime.now().time()
        return now >= dt_time(22, 0) or now <= dt_time(8, 0)
    
    def extract_features(self, hr_data):
        if not hr_data or 'activities-heart-intraday' not in hr_data:
            return None
        
        dataset = hr_data['activities-heart-intraday'].get('dataset', [])
        if not dataset:
            return None
        
        hr_values = [entry['value'] for entry in dataset[-60:] if entry.get('value', 0) > 0]
        
        if len(hr_values) < 10:
            return None
        
        hr_array = np.array(hr_values)
        
        rr_intervals = 60000.0 / hr_array
        rr_diff = np.diff(rr_intervals)
        hrv_rmssd = np.sqrt(np.mean(rr_diff**2)) if len(rr_diff) > 0 else 0
        
        features = {
            'timestamp': datetime.now().isoformat(),
            'mean_hr': float(np.mean(hr_array)),
            'std_hr': float(np.std(hr_array)),
            'min_hr': float(np.min(hr_array)),
            'max_hr': float(np.max(hr_array)),
            'hrv_rmssd': float(hrv_rmssd)
        }
        
        return features
    
    def process_cycle(self):
        if not self.enabled or not self.is_night_time():
            print(f"Skipping: enabled={self.enabled}, night={self.is_night_time()}")
            return
        
        hr_data = self.fitbit.fetch_heart_rate_intraday()
        if not hr_data:
            print("No heart rate data available")
            return
        
        features = self.extract_features(hr_data)
        if not features:
            print("Feature extraction failed")
            return
        
        local_prediction = self.local_model.predict(features)
        print(f"Local Prediction: {local_prediction}")
        
        cloud_prediction = self.cloud_model.predict(features)
        print(f"Cloud Prediction: {cloud_prediction}")
        
        self.storage.save(features, local_prediction)
        
        self.azure.send_telemetry(features, local_prediction)
        
        if local_prediction in ['wake', 'light']:
            print(f"ALARM: Optimal wake time detected - {local_prediction}")
    
    def run(self):
        print("Smart Alarm Edge Started")
        print(f"Fitbit API Enabled: {self.enabled}")
        
        while True:
            try:
                self.process_cycle()
            except Exception as e:
                print(f"Cycle error: {e}")
            
            time.sleep(60)

if __name__ == '__main__':
    app = SmartAlarmEdge()
    app.run()
