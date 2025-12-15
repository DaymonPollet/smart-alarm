import requests
import os

class ModelService:
    def __init__(self, is_cloud=False):
        if is_cloud:
            self.url = os.getenv('CLOUD_MODEL_URL', 'http://localhost:5001/predict')
        else:
            self.url = os.getenv('LOCAL_MODEL_URL', 'http://localhost:5000/predict')
    
    def predict(self, features):
        try:
            response = requests.post(self.url, json=features, timeout=5)
            if response.status_code == 200:
                result = response.json()
                return result.get('prediction', 'UNKNOWN')
        except Exception as e:
            print(f"Model service error: {e}")
        return 'UNKNOWN'
