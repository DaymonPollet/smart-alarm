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


@auth_bp.route('/api/auth/code', methods=['GET', 'POST'])
def manual_code_entry():
    """
    Manual OAuth code entry - for when redirect to localhost fails.
    
    WORKFLOW (when accessing Pi from laptop):
    1. Click "Start Fitbit Authorization" button below
    2. Authorize the app on Fitbit
    3. Fitbit redirects to http://127.0.0.1:8080?code=xxx - THIS FAILS (connection refused)
    4. Copy the 'code' parameter from the failed URL
    5. Paste code in the form and submit
    6. Tokens are exchanged and saved
    """
    if request.method == 'GET':
        # Build the auth URL
        from urllib.parse import urlencode
        params = {
            'client_id': FITBIT_CLIENT_ID,
            'response_type': 'code',
            'scope': 'heartrate activity sleep profile',
            'redirect_uri': FITBIT_REDIRECT_URI
        }
        auth_url = f'https://www.fitbit.com/oauth2/authorize?{urlencode(params)}'
        
        # Check current status
        is_connected = config_store.get('fitbit_connected', False)
        
        # Show a form with instructions
        return f"""
        <html>
            <head><title>Fitbit Authorization</title></head>
            <body style="font-family: Arial; max-width: 700px; margin: 50px auto; padding: 20px;">
                <h2>🔐 Fitbit Authorization</h2>
                
                <div style="padding: 15px; margin-bottom: 20px; border-radius: 8px; background: {'#d4edda' if is_connected else '#fff3cd'};">
                    <strong>Status:</strong> {'✅ Connected' if is_connected else '⚠️ Not Connected'}
                </div>
                
                <div style="background: #e7f3ff; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="margin-top: 0;">📋 Instructions</h3>
                    <ol style="margin-bottom: 0;">
                        <li>Click the <strong>"Start Fitbit Authorization"</strong> button below</li>
                        <li>Log in to Fitbit and authorize the app</li>
                        <li>You'll be redirected to a page that <strong>won't load</strong> (connection refused)</li>
                        <li>Copy the <code>code</code> from the URL: <code>...?code=<strong>COPY_THIS_PART</strong>#_=_</code></li>
                        <li>Paste it in the form below and click Submit</li>
                    </ol>
                </div>
                
                <div style="margin-bottom: 30px;">
                    <a href="{auth_url}" target="_blank" 
                       style="display: inline-block; padding: 12px 24px; background: #00B0B9; color: white; 
                              text-decoration: none; border-radius: 6px; font-weight: bold;">
                        🚀 Start Fitbit Authorization
                    </a>
                </div>
                
                <hr style="margin: 30px 0;">
                
                <h3>Step 2: Paste the code</h3>
                <form method="POST" style="margin-top: 15px;">
                    <input type="text" name="code" placeholder="Paste authorization code here" 
                           style="width: 100%; padding: 12px; font-size: 16px; margin-bottom: 10px; 
                                  border: 2px solid #ddd; border-radius: 6px;">
                    <button type="submit" 
                            style="padding: 12px 24px; font-size: 16px; background: #28a745; color: white; 
                                   border: none; cursor: pointer; border-radius: 6px; font-weight: bold;">
                        ✓ Submit Code
                    </button>
                </form>
                
                <div style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 8px; font-size: 14px;">
                    <strong>Why is this needed?</strong><br>
                    Fitbit requires the redirect URL to be pre-registered. The registered URL is 
                    <code>http://127.0.0.1:8080</code> which only works when running locally. 
                    When accessing from another device (like this Pi), we need to manually copy the code.
                </div>
            </body>
        </html>
        """
    
    # POST - handle code submission
    code = None
    if request.is_json:
        code = request.get_json().get('code')
    else:
        code = request.form.get('code')
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    # Clean up the code (remove any trailing #_=_ or whitespace)
    code = code.strip().split('#')[0].split('&')[0]
    
    print(f"[OAUTH] Manual code entry: {code[:20]}...")
    
    result = handle_oauth_callback(code)
    if result:
        if request.is_json:
            return jsonify({
                "success": True,
                "message": "Fitbit connected successfully!",
                "fitbit_connected": True
            })
        return result
    
    error_msg = "Token exchange failed. The code may have expired (codes are single-use and expire quickly). Please try authorizing again."
    if request.is_json:
        return jsonify({"error": error_msg}), 400
    return f"""
    <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h2 style="color: #dc3545;">Token Exchange Failed</h2>
            <p>{error_msg}</p>
            <a href="/api/auth/code">Try Again</a>
        </body>
    </html>
    """, 400


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
