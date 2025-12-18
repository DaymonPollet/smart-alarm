# Smart Alarm

A cloud-connected sleep monitoring and smart alarm system built for a Cloud Computing course. The system uses Fitbit data, machine learning predictions, and Azure cloud services to provide sleep quality analysis and intelligent wake-up scheduling.

## What This Project Is

- A demonstration of edge-to-cloud architecture with bidirectional synchronization
- A Kubernetes-deployed application running on Raspberry Pi (ARM64)
- An integration of multiple Azure services (IoT Hub, Blob Storage, ML Endpoints)
- A practical implementation of CI/CD with GitHub Actions deploying to self-hosted runners
- A sleep quality prediction system using both local (edge) and cloud ML models

## What This Project Is Not

- A production-ready consumer application
- A medically validated sleep analysis tool
- A replacement for professional sleep studies
- Designed for high availability or scale (single Pi deployment)

## Architecture

```
                    GitHub Actions (CI/CD)
                           |
                           v
+------------------+    Docker Hub    +------------------+
|   Development    | -------------->  |   Raspberry Pi   |
|   (Windows PC)   |                  |   (Kubernetes)   |
+------------------+                  +------------------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
                    v                        v                        v
            +-------------+          +-------------+          +-------------+
            |   Backend   |          |  Frontend   |          |  Storage    |
            |   (Flask)   |          |   (React)   |          |   (PVC)     |
            +-------------+          +-------------+          +-------------+
                    |
        +-----------+-----------+-----------+
        |           |           |           |
        v           v           v           v
    Fitbit API  Azure IoT   Azure ML    Azure Blob
                  Hub       Endpoint     Storage
```

### Components

1. **Backend API** (Flask/Python) - Handles Fitbit OAuth, data fetching, predictions, and Azure integrations
2. **Frontend** (React) - Web dashboard for monitoring, configuration, and alarm management  
3. **Local ML Model** - Random Forest Regressor running on edge for immediate predictions
4. **Cloud ML Model** - Azure ML Endpoint for enhanced classification
5. **Azure IoT Hub** - Device Twin for bidirectional configuration sync
6. **Azure Blob Storage** - Persistent storage for predictions and sleep data
7. **MQTT (HiveMQ)** - Real-time messaging between components

## Features

- Fitbit integration for sleep and heart rate data
- Dual prediction pipeline (local edge model + Azure cloud model)
- Smart alarm with configurable wake window based on sleep stage
- Device Twin synchronization with Azure IoT Hub
- Automatic token refresh for Fitbit OAuth
- Kubernetes deployment with persistent storage
- Background data fetching during alarm monitoring

## Quick Start (Local Development)

### Prerequisites

- Python 3.8+
- Node.js 14+
- Fitbit Developer account

### Setup

1. Clone and create virtual environment:
```powershell
git clone https://github.com/DaymonPollet/smart-alarm.git
cd smart-alarm
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Create `.env` file with required credentials:
```
FITBIT_CLIENT_ID=your_client_id
FITBIT_CLIENT_SECRET=your_client_secret
FITBIT_REDIRECT_URI=http://127.0.0.1:8080
AZURE_ENDPOINT_URL=your_azure_ml_endpoint
AZURE_ENDPOINT_KEY=your_azure_ml_key
AZURE_STORAGE_CONNECTION_STRING=your_storage_connection_string
IOTHUB_DEVICE_CONNECTION_STRING=your_device_connection_string
```

3. Install dependencies:
```powershell
pip install -r backend/local-api/requirements.txt
cd frontend && npm install && cd ..
```

4. Start services:
```powershell
.\start.ps1
```

## Deployment (Raspberry Pi)

The application deploys automatically via GitHub Actions when pushing to main.

### Requirements

- Raspberry Pi 4 with K3s installed
- GitHub Actions self-hosted runner configured
- GitHub Secrets configured for all credentials

### GitHub Secrets Required

- `DOCKER_USERNAME`, `DOCKER_TOKEN`
- `FITBIT_CLIENT_ID`, `FITBIT_CLIENT_SECRET`
- `FITBIT_ACCESS_TOKEN`, `FITBIT_REFRESH_TOKEN`
- `AZURE_ENDPOINT_URL`, `AZURE_ENDPOINT_KEY`
- `AZURE_STORAGE_CONNECTION_STRING`
- `IOTHUB_DEVICE_CONNECTION_STRING`

### Access

After deployment, access the dashboard at:
```
http://<raspberry-pi-ip>:30080
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/config` | GET/POST | Get/update configuration |
| `/api/auth/login` | GET | Start Fitbit OAuth |
| `/api/auth/code` | GET/POST | Manual OAuth code entry |
| `/api/fetch` | POST | Fetch sleep data and predict |
| `/api/alarm` | GET/POST/DELETE | Alarm management |
| `/api/debug/iothub` | GET/POST | IoT Hub diagnostics |
| `/api/debug/blob` | GET/POST | Blob storage diagnostics |

## Project Structure

```
smart-alarm/
├── .github/workflows/     # CI/CD pipeline
├── backend/
│   └── local-api/         # Flask API + services
├── frontend/              # React dashboard
├── k8s/
│   └── base/              # Kubernetes manifests
├── local_model/           # Trained ML models
├── data/                  # Training datasets
└── docs/                  # Setup documentation
```

## Limitations

- Fitbit OAuth redirect only works with `http://127.0.0.1:8080` (Fitbit restriction)
- When accessing from another device, use `/api/auth/code` for manual token entry
- Azure IoT Hub free tier limited to 8000 messages/day (rate limiting implemented)
- Single replica deployment (no HA)
- Requires manual model training before deployment

## Troubleshooting

### Fitbit Shows Disconnected on Pi

1. Tokens must be obtained via OAuth and stored in GitHub Secrets
2. After updating secrets, redeploy to apply changes
3. Use `/api/auth/code` page for manual token entry if needed

### IoT Hub Not Syncing

1. Ensure `IOTHUB_DEVICE_CONNECTION_STRING` (not service connection string) is used
2. Check that the connection string contains `DeviceId=`
3. Verify device exists in Azure IoT Hub

### Blob Storage Not Working

1. Verify `AZURE_STORAGE_CONNECTION_STRING` is set correctly
2. Check that `azure-storage-blob` package is installed
3. Container `smart-alarm-data` is created automatically

## License

Educational project for Howest Cloud Computing course.

## Remote Authentication (Important)

Fitbit OAuth requires a strict Redirect URI match. Most configurations use `http://127.0.0.1:8080`.

**Issue:** When accessing the dashboard from a laptop (e.g., `http://raspberrypi:30080`), the Fitbit login button redirects you to `http://127.0.0.1:8080` on your *laptop*, where the backend is not running.

**Workaround:**
1. Click "Connect Fitbit" on the dashboard.
2. Complete the login on the Fitbit website.
3. When the browser fails to load `http://127.0.0.1:8080...`, look at the URL bar.
4. Copy the `code` parameter from the URL (e.g., `?code=12345abcde...`).
5. Click "Having trouble connecting remotely?" on the dashboard.
6. Paste the code into the manual entry form.

## Troubleshooting

### IoT Hub Message Spikes
The system includes a circuit breaker to prevent accidental message loops (e.g., infinite sync between desired and reported properties). If more than 10 messages are sent in 1 minute, the circuit breaker trips and blocks further reports for that minute.

### "Disconnected" State
If the dashboard shows "Disconnected":
1. Check if `FITBIT_REFRESH_TOKEN` is valid.
2. Use the manual authentication flow described above.
3. Check container logs for specific error messages.
