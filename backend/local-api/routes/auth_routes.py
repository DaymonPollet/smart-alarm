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


def get_redirect_uri(req):
    """
    Get the appropriate redirect URI based on request origin.
    For Pi deployment: uses the host from the request
    For local dev: uses configured FITBIT_REDIRECT_URI
    
    NOTE: The redirect URI must be registered in Fitbit Developer Console!
    For Pi: Register http://<pi-ip>:8080 or http://<pi-hostname>:8080
    """
    # Use configured redirect URI if set and not localhost
    if FITBIT_REDIRECT_URI and '127.0.0.1' not in FITBIT_REDIRECT_URI:
        return FITBIT_REDIRECT_URI
    
    # Try to build from request host
    host = req.headers.get('X-Forwarded-Host') or req.headers.get('Host') or req.host
    scheme = req.headers.get('X-Forwarded-Proto', 'http')
    
    # If accessed via localhost/127.0.0.1, use configured URI
    if '127.0.0.1' in host or 'localhost' in host:
        return FITBIT_REDIRECT_URI or f"{scheme}://{host}"
    
    # For external access, build URI from host
    return f"{scheme}://{host}"


@auth_bp.route('/api/auth/login', methods=['GET'])
def fitbit_login():
    """
    Start Fitbit OAuth flow.
    Returns the authorization URL that the user should visit.
    
    IMPORTANT: The redirect_uri returned must match EXACTLY what's registered
    in the Fitbit Developer Console (dev.fitbit.com).
    """
    redirect_uri = get_redirect_uri(request)
    
    params = {
        'client_id': FITBIT_CLIENT_ID,
        'response_type': 'code',
        'scope': 'heartrate activity sleep profile',
        'redirect_uri': redirect_uri
    }
    
    return jsonify({
        "auth_url": f'https://www.fitbit.com/oauth2/authorize?{urlencode(params)}',
        "redirect_uri": redirect_uri,
        "note": "Ensure this redirect_uri is registered in Fitbit Developer Console"
    })


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


@auth_bp.route('/api/auth/callback', methods=['GET'])
def auth_callback():
    \"\"\"
    OAuth callback endpoint - Fitbit redirects here after user authorizes.
    This provides an alternative to the root callback.
    \"\"\"
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return f\"\"\"
        <html>
            <body style=\"font-family: Arial; text-align: center; padding: 50px;\">
                <h2 style=\"color: #dc3545;\">Authorization Failed</h2>
                <p>Error: {error}</p>
                <p>{request.args.get('error_description', '')}</p>
            </body>
        </html>
        \"\"\", 400
    
    if not code:
        return \"Missing authorization code\", 400
    
    result = handle_oauth_callback(code, request)
    if result:
        return result
    return \"Token exchange failed - check server logs\", 400


def handle_oauth_callback(code, req=None):
    \"\"\"
    Handle OAuth callback with authorization code.
    Uses the request to determine the correct redirect_uri.
    \"\"\"
    # Determine redirect URI - must match what was used in authorization
    if req:
        redirect_uri = get_redirect_uri(req)
    else:
        redirect_uri = FITBIT_REDIRECT_URI
    
    print(f\"[OAUTH] Handling callback with redirect_uri: {redirect_uri}\")
    
    tokens = exchange_code_for_token(code, redirect_uri)
    if tokens:
        set_tokens(tokens['access_token'], tokens['refresh_token'])
        save_tokens_to_env(tokens['access_token'], tokens['refresh_token'])
        save_tokens_to_data_dir(tokens['access_token'], tokens['refresh_token'])
        config_store['fitbit_connected'] = True
        
        print(f\"[OAUTH] Fitbit connected successfully!\")
        
        return \"\"\"
        <html>
            <body style=\"font-family: Arial; text-align: center; padding: 50px;\">
                <h2 style=\"color: #28a745;\">✓ Fitbit Connected Successfully!</h2>
                <p>You can close this window and return to the dashboard.</p>
                <p style=\"color: #6c757d; font-size: 14px;\">The dashboard will update automatically.</p>
                <script>
                    // Try to notify parent window
                    if (window.opener) {
                        window.opener.postMessage('fitbit_connected', '*');
                    }
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
        </html>
        \"\"\"
    
    print(f\"[OAUTH] Token exchange failed\")
    return None
