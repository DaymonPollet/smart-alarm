import requests
import os
from datetime import datetime
from .config import (
    FITBIT_API_BASE, FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET,
    FITBIT_ACCESS_TOKEN, FITBIT_REFRESH_TOKEN, config_store
)

_access_token = FITBIT_ACCESS_TOKEN
_refresh_token = FITBIT_REFRESH_TOKEN

def get_access_token():
    return _access_token

def get_refresh_token():
    return _refresh_token

def set_tokens(access_token, refresh_token):
    global _access_token, _refresh_token
    _access_token = access_token
    _refresh_token = refresh_token

def save_tokens_to_env(access_token, refresh_token):
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith('FITBIT_ACCESS_TOKEN='):
                    f.write(f'FITBIT_ACCESS_TOKEN={access_token}\n')
                elif line.startswith('FITBIT_REFRESH_TOKEN='):
                    f.write(f'FITBIT_REFRESH_TOKEN={refresh_token}\n')
                else:
                    f.write(line)

def refresh_fitbit_token():
    global _access_token, _refresh_token
    
    if not _refresh_token:
        return False
    
    try:
        response = requests.post(
            'https://api.fitbit.com/oauth2/token',
            auth=(FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'refresh_token',
                'refresh_token': _refresh_token
            }
        )
        if response.status_code == 200:
            tokens = response.json()
            _access_token = tokens['access_token']
            _refresh_token = tokens['refresh_token']
            save_tokens_to_env(_access_token, _refresh_token)
            config_store['fitbit_connected'] = True
            return True
    except Exception as e:
        print(f"[FITBIT] Token refresh failed: {e}")
    return False

def fitbit_request(url, method='GET'):
    headers = {'Authorization': f'Bearer {_access_token}'}
    
    try:
        response = requests.request(method, url, headers=headers, timeout=15)
        
        if response.status_code == 401:
            if refresh_fitbit_token():
                headers = {'Authorization': f'Bearer {_access_token}'}
                response = requests.request(method, url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        
        print(f"[FITBIT] API returned {response.status_code}: {url}")
    except Exception as e:
        print(f"[FITBIT] Request error: {e}")
    
    return None

def fetch_heart_rate(date=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    return fitbit_request(f'{FITBIT_API_BASE}/1/user/-/activities/heart/date/{date}/1d.json')

def fetch_heart_rate_for_date(date):
    return fitbit_request(f'{FITBIT_API_BASE}/1/user/-/activities/heart/date/{date}/1d.json')

def fetch_sleep(date=None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    return fitbit_request(f'{FITBIT_API_BASE}/1.2/user/-/sleep/date/{date}.json')

def fetch_sleep_list(limit=30):
    date = datetime.now().strftime('%Y-%m-%d')
    return fitbit_request(
        f'{FITBIT_API_BASE}/1.2/user/-/sleep/list.json?beforeDate={date}&sort=desc&offset=0&limit={limit}'
    )

def fetch_activity(date=None):
    """Fetch daily activity summary (steps, calories, active minutes)"""
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    return fitbit_request(f'{FITBIT_API_BASE}/1/user/-/activities/date/{date}.json')

def fetch_activity_for_date(date):
    """Fetch activity data for a specific date"""
    return fitbit_request(f'{FITBIT_API_BASE}/1/user/-/activities/date/{date}.json')

def exchange_code_for_token(code, redirect_uri):
    try:
        response = requests.post(
            'https://api.fitbit.com/oauth2/token',
            auth=(FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'client_id': FITBIT_CLIENT_ID,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri
            }
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[FITBIT] Token exchange error: {e}")
        return None
