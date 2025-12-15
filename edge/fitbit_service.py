import os
import time
import requests
from datetime import datetime, timedelta
import json

class FitbitService:
    def __init__(self):
        self.client_id = os.getenv('FITBIT_CLIENT_ID')
        self.client_secret = os.getenv('FITBIT_CLIENT_SECRET')
        self.access_token = os.getenv('FITBIT_ACCESS_TOKEN')
        self.refresh_token = os.getenv('FITBIT_REFRESH_TOKEN')
        self.api_base = 'https://api.fitbit.com'
        
    def refresh_access_token(self):
        if not self.refresh_token or self.refresh_token == 'your_refresh_token':
            return False
            
        url = 'https://api.fitbit.com/oauth2/token'
        auth = (self.client_id, self.client_secret)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        
        try:
            response = requests.post(url, auth=auth, headers=headers, data=data)
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens['access_token']
                self.refresh_token = tokens['refresh_token']
                self._update_env_file(tokens['access_token'], tokens['refresh_token'])
                return True
        except Exception as e:
            print(f"Token refresh failed: {e}")
        return False
    
    def _update_env_file(self, access_token, refresh_token):
        env_path = '.env'
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            with open(env_path, 'w') as f:
                for line in lines:
                    if line.startswith('FITBIT_ACCESS_TOKEN='):
                        f.write(f'FITBIT_ACCESS_TOKEN="{access_token}"\n')
                    elif line.startswith('FITBIT_REFRESH_TOKEN='):
                        f.write(f'FITBIT_REFRESH_TOKEN="{refresh_token}"\n')
                    else:
                        f.write(line)
    
    def fetch_heart_rate_intraday(self, date=None):
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        url = f'{self.api_base}/1/user/-/activities/heart/date/{date}/1d/1sec.json'
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 401:
                if self.refresh_access_token():
                    headers = {'Authorization': f'Bearer {self.access_token}'}
                    response = requests.get(url, headers=headers)
                else:
                    return None
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching heart rate: {e}")
        return None
    
    def fetch_sleep_data(self, date=None):
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        url = f'{self.api_base}/1.2/user/-/sleep/date/{date}.json'
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 401:
                if self.refresh_access_token():
                    headers = {'Authorization': f'Bearer {self.access_token}'}
                    response = requests.get(url, headers=headers)
                else:
                    return None
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching sleep data: {e}")
        return None
    
    def fetch_activity_data(self, date=None):
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        url = f'{self.api_base}/1/user/-/activities/steps/date/{date}/1d/1min.json'
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 401:
                if self.refresh_access_token():
                    headers = {'Authorization': f'Bearer {self.access_token}'}
                    response = requests.get(url, headers=headers)
                else:
                    return None
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching activity: {e}")
        return None
