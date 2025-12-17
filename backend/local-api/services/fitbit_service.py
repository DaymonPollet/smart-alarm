import requests
import os
import base64
from datetime import datetime
from .config import (
    FITBIT_API_BASE, FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET,
    FITBIT_ACCESS_TOKEN, FITBIT_REFRESH_TOKEN, config_store
)

_access_token = FITBIT_ACCESS_TOKEN
_refresh_token = FITBIT_REFRESH_TOKEN
_token_refresh_in_progress = False

def get_access_token():
    return _access_token

def get_refresh_token():
    return _refresh_token

def set_tokens(access_token, refresh_token):
    global _access_token, _refresh_token
    _access_token = access_token
    _refresh_token = refresh_token
    print(f"[FITBIT] Tokens updated in memory")

def save_tokens_to_env(access_token, refresh_token):
    """Try to save tokens to .env file (works in local dev, not in K8s)"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
    
    try:
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
            print(f"[FITBIT] Tokens saved to .env file")
    except Exception as e:
        # In K8s, we can't write to .env - tokens stay in memory until pod restart
        print(f"[FITBIT] Could not save to .env (expected in K8s): {e}")

def save_tokens_to_data_dir(access_token, refresh_token):
    """Save tokens to persistent data directory (works in K8s with PVC)"""
    data_dir = os.getenv('DATA_PATH', '/data')
    token_file = os.path.join(data_dir, 'fitbit_tokens.json')
    
    try:
        import json
        os.makedirs(data_dir, exist_ok=True)
        with open(token_file, 'w') as f:
            json.dump({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'updated_at': datetime.now().isoformat()
            }, f)
        print(f"[FITBIT] Tokens saved to {token_file}")
        return True
    except Exception as e:
        print(f"[FITBIT] Could not save to data dir: {e}")
        return False

def load_tokens_from_data_dir():
    """Load tokens from persistent data directory if available"""
    global _access_token, _refresh_token
    
    data_dir = os.getenv('DATA_PATH', '/data')
    token_file = os.path.join(data_dir, 'fitbit_tokens.json')
    
    try:
        import json
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                tokens = json.load(f)
            
            # Only use saved tokens if they exist
            if tokens.get('access_token') and tokens.get('refresh_token'):
                _access_token = tokens['access_token']
                _refresh_token = tokens['refresh_token']
                # Update config_store to reflect that we have tokens
                config_store['fitbit_connected'] = True
                print(f"[FITBIT] Loaded tokens from {token_file} (updated: {tokens.get('updated_at', 'unknown')})")
                return True
    except Exception as e:
        print(f"[FITBIT] Could not load from data dir: {e}")
    
    # Also check if we have tokens from environment (GitHub secrets)
    if _access_token and _refresh_token:
        config_store['fitbit_connected'] = True
        print(f"[FITBIT] Using tokens from environment")
        return True
    
    return False

def refresh_fitbit_token():
    """
    Refresh the Fitbit access token using the refresh token.
    Fitbit tokens expire after 8 hours.
    """
    global _access_token, _refresh_token, _token_refresh_in_progress
    
    # Prevent concurrent refresh attempts
    if _token_refresh_in_progress:
        print(f"[FITBIT] Token refresh already in progress, waiting...")
        import time
        for _ in range(10):  # Wait up to 5 seconds
            time.sleep(0.5)
            if not _token_refresh_in_progress:
                return _access_token is not None
        return False
    
    if not _refresh_token:
        print(f"[FITBIT] No refresh token available - need to re-authenticate")
        config_store['fitbit_connected'] = False
        return False
    
    _token_refresh_in_progress = True
    print(f"[FITBIT] Attempting token refresh...")
    
    try:
        # Fitbit requires Basic auth with client_id:client_secret
        auth_header = base64.b64encode(f"{FITBIT_CLIENT_ID}:{FITBIT_CLIENT_SECRET}".encode()).decode()
        
        response = requests.post(
            'https://api.fitbit.com/oauth2/token',
            headers={
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'grant_type': 'refresh_token',
                'refresh_token': _refresh_token
            },
            timeout=30
        )
        
        if response.status_code == 200:
            tokens = response.json()
            _access_token = tokens['access_token']
            _refresh_token = tokens.get('refresh_token', _refresh_token)  # Fitbit may return new refresh token
            
            print(f"[FITBIT] Token refresh successful!")
            print(f"[FITBIT] New access token: {_access_token[:20]}...")
            
            # Save to persistent storage
            save_tokens_to_data_dir(_access_token, _refresh_token)
            save_tokens_to_env(_access_token, _refresh_token)
            
            config_store['fitbit_connected'] = True
            _token_refresh_in_progress = False
            return True
        else:
            error_msg = response.text
            print(f"[FITBIT] Token refresh failed with status {response.status_code}: {error_msg}")
            
            # If refresh token is invalid, mark as disconnected
            if response.status_code in [400, 401]:
                print(f"[FITBIT] Refresh token invalid or expired - need to re-authenticate via OAuth")
                config_store['fitbit_connected'] = False
            
    except Exception as e:
        print(f"[FITBIT] Token refresh exception: {e}")
    
    _token_refresh_in_progress = False
    return False

# Try to load tokens from persistent storage on module load
load_tokens_from_data_dir()

def fitbit_request(url, method='GET', retry_on_401=True):
    """
    Make a request to the Fitbit API with automatic token refresh on 401.
    """
    global _access_token
    
    if not _access_token:
        print(f"[FITBIT] No access token available")
        config_store['fitbit_connected'] = False
        return None
    
    headers = {'Authorization': f'Bearer {_access_token}'}
    
    try:
        response = requests.request(method, url, headers=headers, timeout=15)
        
        if response.status_code == 401 and retry_on_401:
            print(f"[FITBIT] Got 401, attempting token refresh...")
            if refresh_fitbit_token():
                # Retry with new token
                headers = {'Authorization': f'Bearer {_access_token}'}
                response = requests.request(method, url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    print(f"[FITBIT] Retry successful after token refresh")
                    config_store['fitbit_connected'] = True
                    return response.json()
                else:
                    print(f"[FITBIT] Retry failed with status {response.status_code}")
            else:
                print(f"[FITBIT] Token refresh failed - need to re-authenticate")
                config_store['fitbit_connected'] = False
                return None
        
        if response.status_code == 200:
            config_store['fitbit_connected'] = True
            return response.json()
        
        if response.status_code == 429:
            print(f"[FITBIT] Rate limited (429) - try again later")
        else:
            print(f"[FITBIT] API returned {response.status_code}: {url}")
            
    except requests.exceptions.Timeout:
        print(f"[FITBIT] Request timeout: {url}")
    except requests.exceptions.ConnectionError as e:
        print(f"[FITBIT] Connection error: {e}")
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
    """
    Exchange authorization code for access and refresh tokens.
    The redirect_uri must match exactly what was used in the authorization request.
    """
    try:
        import base64
        auth_header = base64.b64encode(f"{FITBIT_CLIENT_ID}:{FITBIT_CLIENT_SECRET}".encode()).decode()
        
        print(f"[FITBIT] Exchanging code for token with redirect_uri: {redirect_uri}\n")
        
        response = requests.post(
            'https://api.fitbit.com/oauth2/token',
            headers={
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'client_id': FITBIT_CLIENT_ID,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri
            },
            timeout=30
        )
        
        if response.status_code == 200:
            tokens = response.json()
            print(f"[FITBIT] Token exchange successful!\n")
            return tokens
        else:
            print(f"[FITBIT] Token exchange failed: {response.status_code} - {response.text}\n")
            return None
    except Exception as e:
        print(f"[FITBIT] Token exchange error: {e}\n")
        return None
