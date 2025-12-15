# Smart Alarm IoT Project

## Architecture Overview

### Local (Raspberry Pi)
- **Edge Application** (`edge/main.py`): Fetches Fitbit data, processes features, makes predictions
- **API Server** (`edge/api.py`): REST API for frontend and configuration
- **Local Model Service**: Docker container running Flask app with trained model
- **QuestDB**: Local time-series database for storing sleep data

### Cloud (Azure)
- **Azure IoT Hub**: Receives telemetry from edge device
- **Cloud Model Service**: Azure Container App running the same model for comparison
- **Azure Container Registry**: Stores Docker images

### Frontend
- **React Dashboard**: Visualizes sleep data and predictions

## Setup Instructions

### 1. Fitbit API Setup

1. Go to https://dev.fitbit.com/apps
2. You already have an app registered with:
   - Client ID: `23TMGB`
   - Client Secret: `577ff9a33b4dfa2f8b4e7f631028999f`
   - Redirect URL: `http://127.0.0.1:8080/api/oauth/callback`

3. **Get Access Token**:
   - Open browser and go to:
   ```
   https://www.fitbit.com/oauth2/authorize?response_type=code&client_id=23TMGB&redirect_uri=http%3A%2F%2F127.0.0.1%3A8080%2Fapi%2Foauth%2Fcallback&scope=activity%20heartrate%20location%20nutrition%20profile%20settings%20sleep%20social%20weight&expires_in=604800
   ```
   - Authorize the app
   - You'll be redirected to `http://127.0.0.1:8080/api/oauth/callback?code=XXXXXX`
   - Make sure your API server is running, it will automatically exchange the code for tokens and save them to `.env`

### 2. Azure Setup

#### Create Azure Resources

1. **IoT Hub** (Already exists: `HowestTICCFAIDaymon`)
   - Device ID: `RPISmartHome`
   - Connection string already configured

2. **Azure Container Registry** (if not exists):
```bash
az acr create --resource-group <your-rg> --name smartalarmregistry --sku Basic
```

3. **Azure Container App** for Cloud Model:
```bash
az containerapp create \
  --name smart-alarm-model \
  --resource-group <your-rg> \
  --environment <your-env> \
  --image daymonpollet/smart-alarm-model:latest \
  --target-port 5000 \
  --ingress external
```

4. Get the Cloud Model URL and save it as GitHub secret `CLOUD_MODEL_URL`

#### Azure Service Principal for GitHub Actions

```bash
az ad sp create-for-rbac --name "smart-alarm-github" --role contributor \
    --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group> \
    --sdk-auth
```

Save the output JSON as GitHub secret `AZURE_CREDENTIALS`

### 3. GitHub Secrets Configuration

Set these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

```
IOTHUB_CONNECTION_STRING=<from Azure IoT Hub>

FITBIT_CLIENT_ID=<from Fitbit Developer Portal>
FITBIT_CLIENT_SECRET=<from Fitbit Developer Portal>
FITBIT_ACCESS_TOKEN=(will be set after OAuth flow)
FITBIT_REFRESH_TOKEN=(will be set after OAuth flow)

QUEST_DB_USER=admin
QUEST_DB_PASSWORD=<your-password>

DOCKER_USERNAME=<your-docker-username>
DOCKER_TOKEN=<your-docker-token>

AZURE_CREDENTIALS=(JSON from service principal creation)
AZURE_RESOURCE_GROUP=(your resource group name)

CLOUD_MODEL_URL=https://<your-container-app>.azurecontainerapps.io/predict
```

### 4. Local Development Setup

#### On Raspberry Pi

1. **Install QuestDB**:
```bash
docker run -d --name questdb \
  -p 9000:9000 -p 9009:9009 -p 8812:8812 \
  -v ~/questdb:/var/lib/questdb \
  questdb/questdb
```

2. **Clone Repository**:
```bash
git clone <your-repo-url>
cd smart-alarm
```

3. **Setup Edge Application**:
```bash
cd edge
cp .env.example .env
# Edit .env with your actual credentials
pip install -r requirements.txt
```

4. **Train and Deploy Local Model**:
```bash
cd ../backend/python-model-service
pip install -r requirements.txt
python train_model.py
docker build -t smart-alarm-model:latest .
docker run -d -p 5000:5000 --name smart-alarm-model smart-alarm-model:latest
```

5. **Start Edge Services**:
```bash
cd ../../edge
python api.py &  # API server
python main.py &  # Edge application
```

6. **Setup Frontend** (Optional for Pi, or use separate machine):
```bash
cd ../frontend
npm install
npm start
```

### 5. Testing Locally

1. **Check API Health**:
```bash
curl http://localhost:8080/api/health
```

2. **Check Model Service**:
```bash
curl http://localhost:5000/
```

3. **Trigger OAuth Flow** (in browser):
```
http://localhost:8080/api/oauth/callback?code=<your-code>
```

4. **Access Frontend**:
```
http://localhost:3000
```

### 6. Deploy via GitHub Actions

1. **Setup Self-Hosted Runner on Pi**:
   - Go to GitHub repo → Settings → Actions → Runners → New self-hosted runner
   - Follow instructions to install and start runner on Pi

2. **Push to GitHub**:
```bash
git add .
git commit -m "Deploy smart alarm"
git push origin main
```

3. **Monitor Workflows**:
   - Check GitHub Actions tab for deployment progress

## Project Requirements Checklist

- [x] **Sensor**: Fitbit API (heart rate, sleep data)
- [x] **Local Storage**: QuestDB on Raspberry Pi
- [x] **Cloud Forwarding**: Azure IoT Hub telemetry
- [x] **Cloud Storage**: Azure IoT Hub message storage
- [x] **Local AI Model**: Flask service on Pi (Docker)
- [x] **Cloud AI Model**: Azure Container App
- [x] **User Interaction**: React Dashboard
- [x] **Remote Configuration**: API endpoints to enable/disable Fitbit API
- [x] **Raspberry Pi**: Primary edge device

## Model Explanation

### Why Two Models?

**Local Model (Raspberry Pi)**:
- Runs on-device for real-time predictions
- Low latency (<100ms)
- Works offline
- Used for immediate alarm decisions
- Purpose: Edge Computing demonstration

**Cloud Model (Azure)**:
- Same algorithm, deployed in cloud
- Accessible from anywhere
- Can be updated independently
- Used for comparison and redundancy
- Purpose: Cloud Computing demonstration

Both models use **Random Forest Classifier** trained on the same dataset with features:
- Mean Heart Rate
- Heart Rate Std Dev
- Min/Max Heart Rate
- HRV (RMSSD)

## Troubleshooting

### Fitbit API Returns 401
- Access token expired
- Solution: Re-run OAuth flow or check refresh token logic

### QuestDB Connection Failed
- Check if Docker container is running: `docker ps`
- Check port 8812 is accessible

### Model Service Not Responding
- Check Docker container: `docker logs smart-alarm-model`
- Verify port 5000 is free

### Azure IoT Hub Connection Failed
- Verify connection string in `.env`
- Check device is registered in IoT Hub
