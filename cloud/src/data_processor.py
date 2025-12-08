import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class DataProcessor:
    def process_sleep_stages(self, sleep_data: Dict) -> List[Dict]:
        processed_data = []
        for sleep_session in sleep_data.get('sleep', []):
            if not sleep_session.get('isMainSleep', False):
                continue
            
            levels_data = sleep_session.get('levels', {}).get('data', [])
            for level in levels_data:
                processed_data.append({
                    'timestamp': level.get('dateTime'),
                    'sleep_stage': level.get('level'),
                    'duration_seconds': level.get('seconds', 0)
                })
        return processed_data

    def combine_data(self, sleep_stages: List[Dict], hr_data: Dict, hrv_data: Dict, device_id: str) -> Dict:
        hr_dataset = hr_data.get('activities-heart-intraday', {}).get('dataset', [])
        hrv_values = hrv_data.get('hrv', [])
        
        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'data_type': 'sleep_metrics',
            'sleep_stages': sleep_stages,
            'heart_rate': hr_dataset,
            'hrv': hrv_values,
            'device_id': device_id
        }
