# Smart Sleep Alarm System
A complete IoT-based smart alarm system that uses AI to determine the optimal wake-up time based on your sleep cycle data from Fitbit. The system analyzes heart rate variability (HRV), movement patterns, and sleep stages to wake you during light sleep, helping you feel more refreshed.

## Architecture

This system consists of two main components:

### 1. **Cloud Component** (`cloud/fitbit_data_ferry.py`)
- Pulls minute-level sleep data from Fitbit Web API
- Fetches HRV, heart rate, and movement data
- Processes and combines data into a unified format
- Sends data to Azure IoT Hub using the Service SDK

### 2. **Edge Component** (`edge/rpi_smart_alarm.py`)
- Runs on Raspberry Pi 5
- Connects to Azure IoT Hub as a device
- Receives sleep data via cloud-to-device messages
- Runs AI model to analyze sleep stages
- Triggers physical alarm at optimal wake-up time
- Controls buzzer and LED indicators via GPIO

## Data Flow

```
Fitbit API → Data Ferry (Cloud) → Azure IoT Hub → Raspberry Pi → AI Analysis → Smart Alarm
```

1. **Fitbit Data Ferry** fetches your sleep data from Fitbit's cloud
2. Data is sent to **Azure IoT Hub** (cloud message broker)
3. **Raspberry Pi** receives the data as a registered IoT device
4. **AI Model** analyzes sleep stages and predicts optimal wake-up time
5. **Physical Alarm** triggers during light sleep within your target window

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Fitbit account with developer app registered
- Azure subscription with IoT Hub created
- Raspberry Pi 5 (for edge deployment)
- Hardware components (optional for testing):
  - Buzzer/speaker
  - LED indicator
  - Breadboard and jumper wires

### Setup Instructions

#### 1. Clone and Configure

```powershell
# Clone the repository
cd D:\Projects\smart-alarm

# Copy the configuration template
Copy-Item config\.env.template -Destination config\.env

# Edit config\.env with your actual credentials
notepad config\.env
```

#### 2. Set Up Fitbit API Access

1. Go to [Fitbit Developer Portal](https://dev.fitbit.com/apps)
2. Create a new application
3. Set OAuth 2.0 Application Type to **Personal**
4. Note your **Client ID** and **Client Secret**
5. Generate OAuth tokens using Fitbit's OAuth flow
6. Update `config\.env` with your credentials

#### 3. Set Up Azure IoT Hub

```powershell
# Create Resource Group
az group create --name smart-alarm-rg --location eastus

# Create IoT Hub
az iot hub create --name smart-alarm-hub --resource-group smart-alarm-rg --sku F1

# Create Device Identity
az iot hub device-identity create --hub-name smart-alarm-hub --device-id raspberrypi-alarm

# Get IoT Hub connection string (for cloud component)
az iot hub connection-string show --hub-name smart-alarm-hub --policy-name iothubowner

# Get Device connection string (for Raspberry Pi)
az iot hub device-identity connection-string show --hub-name smart-alarm-hub --device-id raspberrypi-alarm
```

Update `config\.env` with these connection strings.

#### 4. Install Dependencies

**For Cloud Component:**
```powershell
cd cloud
pip install -r requirements.txt
```

**For Edge Component (on Raspberry Pi):**
```bash
cd edge
pip install -r requirements.txt

# If running on actual Raspberry Pi, also install:
pip install RPi.GPIO
```

#### 5. Load Environment Variables

**Windows (PowerShell):**
```powershell
# Load from config\.env file
Get-Content config\.env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}
```

**Linux/Raspberry Pi:**
```bash
export $(cat config/.env | xargs)
```

## Usage

### Running the Cloud Data Ferry

```powershell
cd cloud
python fitbit_data_ferry.py
```

This will:
- Fetch your latest sleep data from Fitbit
- Combine HRV, heart rate, and sleep stage data
- Send it to your Raspberry Pi via Azure IoT Hub

### Running the Smart Alarm (Raspberry Pi)

```bash
cd edge
python rpi_smart_alarm.py
```

This will:
- Connect to Azure IoT Hub as a device
- Listen for incoming sleep data
- Analyze your sleep patterns with AI
- Trigger the alarm during optimal light sleep

### Setting Alarm Time

```bash
# Set via environment variable
export ALARM_TIME="07:30"

# Or update it remotely via IoT Hub Direct Method
az iot hub invoke-device-method \
  --hub-name smart-alarm-hub \
  --device-id raspberrypi-alarm \
  --method-name set_alarm \
  --method-payload '{"alarm_time": "07:30"}'
```

## AI Model Features

The sleep stage predictor analyzes:

- **Sleep Stages**: Identifies light, deep, REM, and wake periods
- **Heart Rate Patterns**: Monitors resting heart rate during sleep
- **HRV (Heart Rate Variability)**: Higher HRV indicates better recovery
- **Sleep Quality Score**: Calculated based on deep sleep %, continuity, and HRV
- **Optimal Wake Times**: Predicts best times to wake during light sleep

### Sleep Quality Scoring 
(may be adjusted later)

- **70-100**: Excellent sleep quality
- **50-69**: Good sleep quality
- **30-49**: Fair sleep quality
- **Below 30**: Poor sleep quality

## Hardware Setup (Raspberry Pi)

### GPIO Pinout

```
GPIO 18 (Pin 12) → Buzzer/Speaker (+)
GPIO 23 (Pin 16) → LED (+) → 220Ω Resistor → LED (-)
Ground (Pin 6)   → Buzzer (-) and LED common ground
```

### Wiring Diagram
(Don't know how i'll use this)

```
    Raspberry Pi 5
    ┌─────────────┐
    │             │
    │  GPIO 18 ───┼──→ Buzzer (+)
    │             │
    │  GPIO 23 ───┼──→ LED (+) ──[220Ω]─→ LED (-)
    │             │                          │
    │  GND ───────┼──────────────────────────┴→ Common Ground
    │             │
    └─────────────┘
```

## Remote Control via IoT Hub

The Raspberry Pi supports direct methods for remote control:

### Snooze Alarm
```powershell
az iot hub invoke-device-method `
  --hub-name smart-alarm-hub `
  --device-id raspberrypi-alarm `
  --method-name snooze
```

### Stop Alarm
```powershell
az iot hub invoke-device-method `
  --hub-name smart-alarm-hub `
  --device-id raspberrypi-alarm `
  --method-name stop_alarm
```

### Get Status
```powershell
az iot hub invoke-device-method `
  --hub-name smart-alarm-hub `
  --device-id raspberrypi-alarm `
  --method-name get_status
```

## Project Structure

```
smart-alarm/
├── cloud/                      # Cloud components
│   ├── fitbit_data_ferry.py   # Fitbit API to IoT Hub bridge
│   └── requirements.txt        # Cloud dependencies
├── edge/                       # Edge components
│   ├── rpi_smart_alarm.py     # Raspberry Pi alarm controller
│   └── requirements.txt        # Edge dependencies
├── config/                     # Configuration
│   └── .env.template          # Environment variable template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

##  Security Best Practices

1. **Never commit `.env` file** to version control
2. **Use Azure Key Vault** for production deployments
3. **Rotate credentials regularly**
4. **Use device provisioning service** for fleet management
5. **Enable IoT Hub monitoring** and alerts

## Troubleshooting

### Cloud Component Issues

**Problem**: `fitbit` module import error
```powershell
pip install fitbit
```

**Problem**: Azure authentication fails
- Verify your IoT Hub connection string is correct
- Ensure it has `iothubowner` permissions

### Edge Component Issues

**Problem**: Cannot connect to IoT Hub
- Check device connection string
- Verify device is registered in IoT Hub
- Check network connectivity

**Problem**: GPIO errors on non-Pi systems
- The code runs in simulation mode when `RPi.GPIO` is not available
- This is normal for development/testing on Windows/Mac

**Problem**: No sleep data received
- Ensure cloud component is running and sending data
- Check IoT Hub message routing
- Verify device ID matches in both components

## Future Enhancements

- [ ] Machine learning model training on personal sleep data
- [ ] Mobile app for configuration and monitoring
- [ ] Integration with additional wearables (Apple Watch, Garmin)
- [ ] Weather-aware wake-up adjustments
- [ ] Gradual light/sound alarm (sunrise simulation)
- [ ] Sleep report generation and trends
- [ ] Multi-user support for couples

## License

Proprietary License of Daymon Pollet and no one else.
## Contributing

Me, myself, and I

## Support

For issues or questions, please check the troubleshooting section above.

---

**Built with** ❤️ **using Python, Azure IoT Hub, Fitbit API, and Raspberry Pi, maybe gonne do it in a better language like Java soon**
