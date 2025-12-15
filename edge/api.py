import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from storage_service import StorageService
from fitbit_service import FitbitService

load_dotenv()

app = Flask(__name__)
CORS(app)

storage = StorageService()
fitbit = FitbitService()

config_state = {
    'fitbit_enabled': os.getenv('ENABLE_FITBIT_API', 'false').lower() == 'true'
}

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/data', methods=['GET'])
def get_data():
    limit = request.args.get('limit', 100, type=int)
    data = storage.get_recent(limit)
    return jsonify(data)

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(config_state)

@app.route('/api/config', methods=['POST'])
def update_config():
    data = request.json
    if 'fitbit_enabled' in data:
        config_state['fitbit_enabled'] = data['fitbit_enabled']
        
        env_path = '.env'
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            with open(env_path, 'w') as f:
                found = False
                for line in lines:
                    if line.startswith('ENABLE_FITBIT_API='):
                        f.write(f"ENABLE_FITBIT_API={'true' if data['fitbit_enabled'] else 'false'}\n")
                        found = True
                    else:
                        f.write(line)
                
                if not found:
                    f.write(f"\nENABLE_FITBIT_API={'true' if data['fitbit_enabled'] else 'false'}\n")
    
    return jsonify({'status': 'updated', 'config': config_state})

@app.route('/api/oauth/callback', methods=['GET'])
def oauth_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    import requests
    
    client_id = os.getenv('FITBIT_CLIENT_ID')
    client_secret = os.getenv('FITBIT_CLIENT_SECRET')
    
    url = 'https://api.fitbit.com/oauth2/token'
    auth = (client_id, client_secret)
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'client_id': client_id,
        'grant_type': 'authorization_code',
        'redirect_uri': 'http://localhost:8080/api/oauth/callback',
        'code': code
    }
    
    try:
        response = requests.post(url, auth=auth, headers=headers, data=data)
        if response.status_code == 200:
            tokens = response.json()
            
            env_path = '.env'
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            with open(env_path, 'w') as f:
                for line in lines:
                    if line.startswith('FITBIT_ACCESS_TOKEN='):
                        f.write(f"FITBIT_ACCESS_TOKEN=\"{tokens['access_token']}\"\n")
                    elif line.startswith('FITBIT_REFRESH_TOKEN='):
                        f.write(f"FITBIT_REFRESH_TOKEN=\"{tokens['refresh_token']}\"\n")
                    else:
                        f.write(line)
            
            return jsonify({'status': 'success', 'message': 'Tokens saved'})
        else:
            return jsonify({'error': 'Token exchange failed', 'details': response.text}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
