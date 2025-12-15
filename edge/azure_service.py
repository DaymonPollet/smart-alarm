import os
import json
from azure.iot.device import IoTHubDeviceClient, Message

class AzureService:
    def __init__(self):
        self.connection_string = os.getenv('IOTHUB_CONNECTION_STRING')
        self.client = None
        
    def connect(self):
        if not self.connection_string:
            print("IoT Hub connection string not set")
            return False
        
        try:
            self.client = IoTHubDeviceClient.create_from_connection_string(self.connection_string)
            self.client.connect()
            return True
        except Exception as e:
            print(f"Azure connection failed: {e}")
            return False
    
    def send_telemetry(self, data, prediction):
        if not self.client:
            return False
        
        try:
            payload = {
                'timestamp': data.get('timestamp'),
                'mean_hr': data.get('mean_hr'),
                'std_hr': data.get('std_hr'),
                'min_hr': data.get('min_hr'),
                'max_hr': data.get('max_hr'),
                'hrv_rmssd': data.get('hrv_rmssd'),
                'prediction': prediction
            }
            
            message = Message(json.dumps(payload))
            message.content_encoding = "utf-8"
            message.content_type = "application/json"
            
            self.client.send_message(message)
            return True
        except Exception as e:
            print(f"Telemetry send failed: {e}")
            return False
    
    def disconnect(self):
        if self.client:
            self.client.disconnect()
