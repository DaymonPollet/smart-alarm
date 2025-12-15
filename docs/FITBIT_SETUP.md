# Fitbit API Configuration

## Step 1: Verify Your Application

Register a Fitbit application registered:
- **Client ID**: `23TMGB`
- **Client Secret**: `577ff9a33b4dfa2f8b4e7f631028999f`
- **Redirect URL**: `http://127.0.0.1:8080/api/oauth/callback`

## Step 2: OAuth Flow to Get Access Token

### Option A: Manual OAuth Flow

1. **Start your API server**:
```bash
cd edge
python api.py
```

2. **Open browser and navigate to**:
```
https://www.fitbit.com/oauth2/authorize?response_type=code&client_id=23TMGB&redirect_uri=http%3A%2F%2F127.0.0.1%3A8080%2Fapi%2Foauth%2Fcallback&scope=activity%20heartrate%20location%20nutrition%20profile%20settings%20sleep%20social%20weight&expires_in=604800
```

3. **Login to Fitbit and authorize** the application

4. **You'll be redirected to**:
```
http://127.0.0.1:8080/api/oauth/callback?code=XXXXXX
```

5. **The API server will automatically**:
   - Exchange the code for access and refresh tokens
   - Save them to your `.env` file
   - Display success message

### Option B: Use curl

If you already have an authorization code:

```bash
curl -X POST https://api.fitbit.com/oauth2/token \
  -H "Authorization: Basic $(echo -n '23TMGB:577ff9a33b4dfa2f8b4e7f631028999f' | base64)" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=23TMGB&grant_type=authorization_code&redirect_uri=http://127.0.0.1:8080/api/oauth/callback&code=YOUR_CODE_HERE"
```

Save the `access_token` and `refresh_token` from the response to your `.env` file.

## Step 3: Update .env File

Your `.env` file should contain:
```bash
FITBIT_CLIENT_ID="23TMGB"
FITBIT_CLIENT_SECRET="577ff9a33b4dfa2f8b4e7f631028999f"
FITBIT_ACCESS_TOKEN="eyJhbGciOiJIUzI1NiJ9..."
FITBIT_REFRESH_TOKEN="abc123def456..."
```

## Step 4: Update GitHub Secrets

Add these to GitHub Secrets:
```
FITBIT_CLIENT_ID=23TMGB
FITBIT_CLIENT_SECRET=577ff9a33b4dfa2f8b4e7f631028999f
FITBIT_ACCESS_TOKEN=<your-access-token>
FITBIT_REFRESH_TOKEN=<your-refresh-token>
```

## Step 5: Token Refresh

The application automatically refreshes tokens when they expire. The refresh token is valid for 1 year. When it refreshes:
- New tokens are saved to `.env`
- You should update GitHub Secrets with new tokens periodically

## Verify API Access

Test your token:
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  https://api.fitbit.com/1/user/-/profile.json
```

## Scopes Required

Your app needs these scopes:
- `activity`: For activity data
- `heartrate`: For heart rate data (required)
- `sleep`: For sleep stage data (required)
- `profile`: For user profile

## Rate Limits

Fitbit API has rate limits:
- **150 requests per hour** per user
- Our app queries once per minute = 60 requests/hour
- Only queries between 22:00-08:00 (10 hours) = 600 requests max
- With 1/min rate = 600 requests total

This is within limits, but the app defaults to disabled. Enable via dashboard only when needed.

## Troubleshooting

### "Invalid token" error
- Token expired: Re-run OAuth flow
- Check token in `.env` has no extra quotes or spaces

### "Rate limit exceeded"
- Disable Fitbit API via dashboard
- Wait until next hour
- Increase polling interval in `main.py` (change `time.sleep(60)` to `time.sleep(120)`)

### "Insufficient scope"
- Re-authorize app with all scopes in authorization URL
