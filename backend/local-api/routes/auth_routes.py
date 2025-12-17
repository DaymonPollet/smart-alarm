"""
Auth Routes - Fitbit OAuth handling

IMPORTANT: Fitbit OAuth requires redirect_uri to EXACTLY match what's registered
in the Fitbit Developer Console (dev.fitbit.com).

To use this on Raspberry Pi:
1. Go to dev.fitbit.com -> Manage My Apps -> Your App
2. Add your Pi's address to "Redirect URL", e.g.:
   - http://192.168.0.207:30080  (if using NodePort)
   - http://192.168.0.207:8080   (if accessing backend directly)
3. Set FITBIT_REDIRECT_URI in your .env or K8s secrets to match exactly
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
    """
    Start Fitbit OAuth flow.
    Returns the authorization URL that the user should visit.
    
    The redirect_uri MUST be registered in Fitbit Developer Console!
    """
    # Always use the configured redirect URI - it must match Fitbit's registration
    redirect_uri = FITBIT_REDIRECT_URI
    
    if not redirect_uri:
        return jsonify({
            "error": "FITBIT_REDIRECT_URI not configured",
            "hint": "Set FITBIT_REDIRECT_URI in environment variables"
        }), 500
    
    params = {
        'client_id': FITBIT_CLIENT_ID,
        'response_type': 'code',
        'scope': 'heartrate activity sleep profile',
        'redirect_uri': redirect_uri
    }
    
    return jsonify({
        "auth_url": f'https://www.fitbit.com/oauth2/authorize?{urlencode(params)}',
        "redirect_uri": redirect_uri,
        "note": "This redirect_uri must be registered at dev.fitbit.com"
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
    """
    OAuth callback endpoint - Fitbit redirects here after user authorizes.
    This provides an alternative to the root callback.
    """
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return f"""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2 style="color: #dc3545;">Authorization Failed</h2>
                <p>Error: {error}</p>
                <p>{request.args.get('error_description', '')}</p>
            </body>
        </html>
        """, 400
    
    if not code:
        return "Missing authorization code", 400
    
    result = handle_oauth_callback(code)
    if result:
        return result
    return "Token exchange failed - check server logs", 400


def handle_oauth_callback(code):
    """
    Handle OAuth callback with authorization code.
    Always uses the configured FITBIT_REDIRECT_URI (must match Fitbit registration).
    """
    redirect_uri = FITBIT_REDIRECT_URI
    
    print(f"[OAUTH] Handling callback with redirect_uri: {redirect_uri}")
    
    tokens = exchange_code_for_token(code, redirect_uri)
    if tokens:
        set_tokens(tokens['access_token'], tokens['refresh_token'])
        save_tokens_to_env(tokens['access_token'], tokens['refresh_token'])
        save_tokens_to_data_dir(tokens['access_token'], tokens['refresh_token'])
        config_store['fitbit_connected'] = True
        
        print(f"[OAUTH] Fitbit connected successfully!")
        
        return """
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2 style="color: #28a745;">✓ Fitbit Connected Successfully!</h2>
                <p>You can close this window and return to the dashboard.</p>
                <p style="color: #6c757d; font-size: 14px;">The dashboard will update automatically.</p>
                <script>
                    // Try to notify parent window
                    if (window.opener) {
                        window.opener.postMessage('fitbit_connected', '*');
                    }
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
        </html>
        """
    
    print(f"[OAUTH] Token exchange failed")
    return None
