"""
Azure Application Insights service for logging predictions to cloud.
"""

import os
from datetime import datetime
from .config import config_store

APPINSIGHTS_CONNECTION_STRING = os.getenv('APPINSIGHTS_CONNECTION_STRING', '')

telemetry_client = None

def init_insights():
    global telemetry_client
    
    if not APPINSIGHTS_CONNECTION_STRING:
        print("[INSIGHTS] No connection string configured")
        return False
    
    try:
        from opencensus.ext.azure import metrics_exporter
        from opencensus.ext.azure.log_exporter import AzureLogHandler
        import logging
        
        logger = logging.getLogger('smart-alarm')
        logger.addHandler(AzureLogHandler(connection_string=APPINSIGHTS_CONNECTION_STRING))
        logger.setLevel(logging.INFO)
        
        telemetry_client = logger
        config_store['insights_connected'] = True
        print("[INSIGHTS] Connected to Application Insights")
        return True
    except ImportError:
        print("[INSIGHTS] opencensus-ext-azure not installed, using simple HTTP logging")
        telemetry_client = 'http'
        return True
    except Exception as e:
        print(f"[INSIGHTS] Init error: {e}")
        return False

def log_prediction_to_cloud(prediction_data):
    if not APPINSIGHTS_CONNECTION_STRING:
        return False
    
    try:
        if telemetry_client == 'http':
            import requests
            import json
            
            ikey = APPINSIGHTS_CONNECTION_STRING.split('InstrumentationKey=')[1].split(';')[0] if 'InstrumentationKey=' in APPINSIGHTS_CONNECTION_STRING else ''
            
            if not ikey:
                return False
            
            telemetry = {
                "name": "Microsoft.ApplicationInsights.Event",
                "time": datetime.utcnow().isoformat() + "Z",
                "iKey": ikey,
                "data": {
                    "baseType": "EventData",
                    "baseData": {
                        "name": "SleepPrediction",
                        "properties": {
                            "timestamp": prediction_data.get('timestamp', ''),
                            "local_quality": prediction_data.get('local_quality', ''),
                            "local_score": str(prediction_data.get('local_score', 0)),
                            "cloud_quality": prediction_data.get('cloud_quality', ''),
                            "cloud_confidence": str(prediction_data.get('cloud_confidence', 0)),
                            "deep_sleep_minutes": str(prediction_data.get('deep_sleep_minutes', 0)),
                            "resting_heart_rate": str(prediction_data.get('resting_heart_rate', 0)),
                            "duration_hours": str(prediction_data.get('duration_hours', 0)),
                            "efficiency": str(prediction_data.get('efficiency', 0))
                        }
                    }
                }
            }
            
            response = requests.post(
                "https://dc.services.visualstudio.com/v2/track",
                headers={"Content-Type": "application/json"},
                data=json.dumps([telemetry]),
                timeout=5
            )
            
            if response.status_code in [200, 206]:
                config_store['insights_connected'] = True
                return True
            else:
                print(f"[INSIGHTS] HTTP {response.status_code}")
                return False
                
        elif telemetry_client:
            telemetry_client.info(
                "SleepPrediction",
                extra={
                    "custom_dimensions": {
                        "timestamp": prediction_data.get('timestamp', ''),
                        "local_quality": prediction_data.get('local_quality', ''),
                        "local_score": prediction_data.get('local_score', 0),
                        "cloud_quality": prediction_data.get('cloud_quality', ''),
                        "cloud_confidence": prediction_data.get('cloud_confidence', 0),
                        "deep_sleep_minutes": prediction_data.get('deep_sleep_minutes', 0),
                        "resting_heart_rate": prediction_data.get('resting_heart_rate', 0)
                    }
                }
            )
            return True
    except Exception as e:
        print(f"[INSIGHTS] Log error: {e}")
        config_store['insights_connected'] = False
        return False
    
    return False
