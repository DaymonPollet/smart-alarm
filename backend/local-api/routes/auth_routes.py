"""
Auth Routes - Fitbit OAuth handling
"""
from flask import Blueprint, request, jsonify
from urllib.parse import urlencode

from services.config import FITBIT_CLIENT_ID, FITBIT_REDIRECT_URI, config_store
from services.fitbit_service import (
    exchange_code_for_token, save_tokens_to_env, set_tokens,
    get_access_token, get_refresh_token, refresh_fitbit_token,
    save_tokens_to_data_dir
)

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


@auth_bp.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Get current Fitbit authentication status"""
    access_token = get_access_token()
    refresh_token = get_refresh_token()
    
    return jsonify({
        'fitbit_connected': config_store.get('fitbit_connected', False),
        'has_access_token': bool(access_token),
        'has_refresh_token': bool(refresh_token),
        'access_token_preview': f"{access_token[:20]}..." if access_token else None,
        'refresh_token_preview': f"{refresh_token[:10]}..." if refresh_token else None
    })


@auth_bp.route('/api/auth/refresh', methods=['POST'])
def manual_refresh():
    """Manually trigger token refresh"""
    success = refresh_fitbit_token()
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Token refreshed successfully',
            'fitbit_connected': True
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Token refresh failed - may need to re-authenticate via OAuth',
            'fitbit_connected': False
        }), 400


def handle_oauth_callback(code):
    """Handle OAuth callback with authorization code"""
    tokens = exchange_code_for_token(code, FITBIT_REDIRECT_URI)
    if tokens:
        set_tokens(tokens['access_token'], tokens['refresh_token'])
        save_tokens_to_env(tokens['access_token'], tokens['refresh_token'])
        save_tokens_to_data_dir(tokens['access_token'], tokens['refresh_token'])
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
