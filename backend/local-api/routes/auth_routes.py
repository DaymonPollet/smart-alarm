"""
Auth Routes - Fitbit OAuth handling
"""
from flask import Blueprint, request, jsonify
from urllib.parse import urlencode

from services.config import FITBIT_CLIENT_ID, FITBIT_REDIRECT_URI, config_store
from services.fitbit_service import exchange_code_for_token, save_tokens_to_env, set_tokens

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/login', methods=['GET'])
def fitbit_login():
    """Start Fitbit OAuth flow"""
    params = {
        'client_id': FITBIT_CLIENT_ID,
        'response_type': 'code',
        'scope': 'heartrate activity sleep profile',
        'redirect_uri': FITBIT_REDIRECT_URI
    }
    return jsonify({"auth_url": f'https://www.fitbit.com/oauth2/authorize?{urlencode(params)}'})


def handle_oauth_callback(code):
    """Handle OAuth callback with authorization code"""
    tokens = exchange_code_for_token(code, FITBIT_REDIRECT_URI)
    if tokens:
        set_tokens(tokens['access_token'], tokens['refresh_token'])
        save_tokens_to_env(tokens['access_token'], tokens['refresh_token'])
        config_store['fitbit_connected'] = True
        return """
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2 style="color: #28a745;">Fitbit Connected Successfully!</h2>
                <p>You can close this window and return to the dashboard.</p>
                <script>setTimeout(() => window.close(), 2000);</script>
            </body>
        </html>
        """
    return None
