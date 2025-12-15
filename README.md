# Smart Alarm

A smart alarm system that monitors sleep stages using heart rate data from Fitbit and machine learning predictions.

## Features

- Real-time heart rate monitoring via Fitbit API
- Machine learning model for sleep stage prediction (Awake, Deep Sleep, Light Sleep)
- Web dashboard for monitoring and configuration
- Automated alarm triggering based on optimal wake times

## Architecture

The application consists of three main components:

1. **Model Service** - Python ML service that predicts sleep stages from heart rate data
2. **Backend API** - Flask API that handles Fitbit integration and data management
3. **Frontend** - React web dashboard for monitoring and control

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher
- Fitbit Developer account with registered application

### Setup

1. Clone the repository and navigate to the project directory

2. Create a virtual environment:
```powershell
python -m venv .venv
```

3. Create a `.env` file in the root directory with your Fitbit credentials:
```
FITBIT_CLIENT_ID=your_client_id
FITBIT_CLIENT_SECRET=your_client_secret
FITBIT_REDIRECT_URI=http://127.0.0.1:8080/api/oauth/callback
MODEL_SERVICE_URL=http://localhost:5000
API_PORT=8080
```

4. Install Python dependencies:
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r backend/local-api/requirements.txt
pip install -r backend/python-model-service/requirements.txt
```

5. Install frontend dependencies:
```powershell
cd frontend
npm install
cd ..
```

### Running the Application

Start all services with one command:
```powershell
.\start-all.ps1
```

This will launch:
- Model Service on http://localhost:5000
- Backend API on http://localhost:8080
- Frontend on http://localhost:3000

The frontend will automatically open in your browser.

### Stopping the Application

```powershell
.\stop-all.ps1
```

## Usage

1. **Connect Fitbit**: Click "Connect Fitbit" in the dashboard and authorize the application
2. **Fetch Data**: Use "Fetch Now" to manually retrieve heart rate data and get a prediction
3. **Enable Monitoring**: Toggle monitoring to continuously track sleep stages
4. **View Data**: Monitor real-time predictions and heart rate data in the dashboard

## Fitbit OAuth Setup

To connect your Fitbit account:

1. Register an application at https://dev.fitbit.com/apps
2. Set the OAuth 2.0 Redirect URL to: `http://127.0.0.1:8080/api/oauth/callback`
3. Request these scopes: activity, heartrate, sleep, profile
4. Add your Client ID and Secret to the `.env` file

The application will automatically handle token refresh.

## API Endpoints

### Backend API (http://localhost:8080)

- `GET /api/health` - Health check
- `GET /api/config` - Get application configuration
- `GET /api/auth/login` - Start Fitbit OAuth flow
- `GET /api/oauth/callback` - OAuth callback handler
- `POST /api/fetch` - Fetch heart rate data and predict sleep stage
- `GET /api/data` - Get stored predictions
- `POST /api/predict` - Make prediction from provided data

### Model Service (http://localhost:5000)

- `GET /health` - Health check
- `POST /predict` - Predict sleep stage from features

## Project Structure

```
smart-alarm/
├── backend/
│   ├── local-api/          # Flask API server
│   └── python-model-service/ # ML model service
├── frontend/               # React web dashboard
├── data/                   # Training data
├── .env                    # Environment configuration
├── start-all.ps1          # Startup script
└── stop-all.ps1           # Shutdown script
```

## Development

### Training the Model

```powershell
cd backend/python-model-service
python train_model.py
```

This will create `model.joblib` with the trained classifier.

### Running Individual Services

Model Service:
```powershell
cd backend/python-model-service
python app.py
```

Backend API:
```powershell
cd backend/local-api
python app.py
```

Frontend:
```powershell
cd frontend
npm start
```

## Troubleshooting

### Fitbit Connection Issues

If you get "invalid_request - Invalid redirect_uri parameter value":
- Ensure `FITBIT_REDIRECT_URI` in `.env` matches exactly what is registered in your Fitbit app
- Check that the backend API is running on port 8080
- Verify the route is `/api/oauth/callback` not just `/callback`

### Port Already in Use

If services fail to start due to port conflicts:
- Model Service: Change port in `backend/python-model-service/app.py`
- Backend API: Change `API_PORT` in `.env`
- Frontend: Change port in `frontend/package.json` or set `PORT` environment variable

### Module Not Found

Ensure the virtual environment is activated:
```powershell
.\.venv\Scripts\Activate.ps1
```

Then reinstall dependencies:
```powershell
pip install -r backend/local-api/requirements.txt
pip install -r backend/python-model-service/requirements.txt
```

## License

This project is for educational purposes.
