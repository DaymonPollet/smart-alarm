# Architecture Documentation 🏗️

## System Overview

The Smart Sleep Alarm is a distributed IoT system with three main layers:

1. **Data Source Layer**: Fitbit Cloud API
2. **Cloud Processing Layer**: Azure IoT Hub + Data Ferry
3. **Edge Intelligence Layer**: Raspberry Pi with AI model

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCE LAYER                                │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      Fitbit Cloud API                             │   │
│  │  - Sleep Stages (light, deep, REM, wake)                         │   │
│  │  - Heart Rate (minute-level)                                     │   │
│  │  - HRV (Heart Rate Variability)                                  │   │
│  │  - Movement Patterns                                             │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
└────────────────────────────┼─────────────────────────────────────────────┘
                             │ HTTPS REST API
                             │ OAuth 2.0 Authentication
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CLOUD PROCESSING LAYER                              │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              Fitbit Data Ferry (Python)                          │   │
│  │  • Pulls data from Fitbit API every night                       │   │
│  │  • Processes and combines sleep metrics                         │   │
│  │  • Formats data for IoT transmission                            │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                            │                                              │
│                            │ Azure IoT Hub Service SDK                    │
│                            │ Cloud-to-Device Messages                     │
│                            ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Azure IoT Hub                                 │   │
│  │  • Device registry and authentication                            │   │
│  │  • Bi-directional messaging                                     │   │
│  │  • Direct methods (remote control)                              │   │
│  │  • Device twin (state management)                               │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
└────────────────────────────┼─────────────────────────────────────────────┘
                             │ AMQP/MQTT Protocol
                             │ Encrypted Connection
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    EDGE INTELLIGENCE LAYER                               │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              Raspberry Pi 5 Smart Alarm                          │   │
│  │                                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │  IoT Hub Device Client                                   │  │   │
│  │  │  • Connects to Azure IoT Hub                            │  │   │
│  │  │  • Receives sleep data messages                         │  │   │
│  │  │  • Handles direct method calls                          │  │   │
│  │  │  • Sends telemetry back to cloud                        │  │   │
│  │  └──────────────┬───────────────────────────────────────────┘  │   │
│  │                 │                                                │   │
│  │                 ▼                                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │  Sleep Stage Predictor (AI Model)                       │  │   │
│  │  │  • Analyzes sleep stages                                │  │   │
│  │  │  • Calculates sleep quality score                       │  │   │
│  │  │  • Identifies light sleep periods                       │  │   │
│  │  │  • Predicts optimal wake-up times                       │  │   │
│  │  │  • Confidence scoring                                   │  │   │
│  │  └──────────────┬───────────────────────────────────────────┘  │   │
│  │                 │                                                │   │
│  │                 ▼                                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │  Smart Alarm Controller                                  │  │   │
│  │  │  • Evaluates wake-up conditions                         │  │   │
│  │  │  • Controls GPIO pins                                   │  │   │
│  │  │  • Manages alarm state                                  │  │   │
│  │  │  • Handles snooze logic                                 │  │   │
│  │  └──────────────┬───────────────────────────────────────────┘  │   │
│  │                 │                                                │   │
│  │                 ▼                                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │  Physical Hardware                                       │  │   │
│  │  │  GPIO 18 → Buzzer/Speaker                               │  │   │
│  │  │  GPIO 23 → LED Indicator                                │  │   │
│  │  └──────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Sequence

### Morning Routine (Automated)

```
1. Sleep Detection
   User sleeps → Fitbit tracks continuously → Data stored in Fitbit Cloud

2. Data Collection (e.g., 6:00 AM)
   Data Ferry runs → Fetches last 8 hours of sleep data → Processes metrics

3. Data Transmission
   Ferry sends to IoT Hub → Hub routes to Raspberry Pi device

4. AI Analysis
   Pi receives data → AI model analyzes sleep stages → Identifies light sleep

5. Smart Wake Decision
   Current time: 6:45 AM
   Target time: 7:00 AM
   Current stage: Light Sleep
   Decision: TRIGGER ALARM NOW ✓

6. Alarm Activation
   GPIO signals → Buzzer sounds → LED lights up → User wakes up refreshed!

7. User Interaction
   Option 1: Stop alarm → GPIO off → Success!
   Option 2: Snooze → 5 min delay → Repeat from step 5
```

## Component Interactions

### Cloud Component (`fitbit_data_ferry.py`)

```python
┌─────────────────────────────────────────────┐
│  FitbitDataFerry Class                      │
├─────────────────────────────────────────────┤
│  Methods:                                   │
│  • fetch_sleep_data()                       │
│  • fetch_heart_rate_intraday()             │
│  • fetch_hrv_data()                        │
│  • process_sleep_stages()                   │
│  • combine_data_for_alarm()                │
│  • send_to_iot_hub()                       │
│  • run_data_ferry()        ← Main Pipeline │
└─────────────────────────────────────────────┘
         │
         ├──→ Fitbit API Client
         │    • OAuth 2.0 authentication
         │    • Rate limiting handling
         │    • Token refresh
         │
         └──→ Azure IoT Hub Registry Manager
              • Send cloud-to-device messages
              • Connection string authentication
```

### Edge Component (`rpi_smart_alarm.py`)

```python
┌─────────────────────────────────────────────┐
│  RaspberryPiSmartAlarm Class                │
├─────────────────────────────────────────────┤
│  Components:                                │
│  • IoTHubDeviceClient                      │
│  • SleepStagePredictor (AI)               │
│  • SmartAlarmController                    │
├─────────────────────────────────────────────┤
│  Message Handlers:                          │
│  • message_handler()     ← Receives data   │
│  • method_handler()      ← Remote control  │
│  • evaluate_wake_up_decision()             │
│  • trigger_optimal_alarm()                 │
└─────────────────────────────────────────────┘
         │
         ├──→ SleepStagePredictor
         │    • analyze_sleep_data()
         │    • calculate_sleep_quality()
         │    • predict_optimal_wake_times()
         │
         ├──→ SmartAlarmController
         │    • trigger_alarm()
         │    • stop_alarm()
         │    • snooze()
         │
         └──→ RPi.GPIO
              • PWM for buzzer
              • Digital output for LED
```

## AI Model Details

### Sleep Stage Predictor Algorithm

```
Input: 
  - Sleep stages array (timestamp, stage, duration)
  - Heart rate data (minute-by-minute)
  - HRV values (RMSSD)

Process:
  1. Identify Light Sleep Periods
     • Filter stages where level = "light"
     • Require minimum 5-minute duration
     • Store timestamps
  
  2. Calculate Sleep Quality (0-100 scale)
     Base Score: 50
     + Deep Sleep % * 0.5 (max +20 points)
     - Wake Count * 2 (max -15 points)
     + HRV Quality (0/5/15 points based on RMSSD)
     = Final Score
  
  3. Predict Optimal Wake Times
     For each light sleep period:
       - Calculate confidence = duration_score
       - Add contextual factors (HR stability, time of day)
       - Rank by confidence
     Return top 5 candidates

Output:
  - Light sleep periods with timestamps
  - Sleep quality score
  - Ranked optimal wake times with confidence
  - Current sleep stage
```

### Decision Logic

```
Alarm Window: [Target Time - 30 min, Target Time]

IF current_time in alarm_window:
    IF current_stage == "light" AND confidence > 70%:
        TRIGGER ALARM → Optimal wake-up!
    ELSE:
        WAIT for light sleep (check every minute)
        IF current_time > target_time:
            TRIGGER ALARM → Time's up!
ELSE:
    WAIT (monitor only)
```

## Security Architecture

```
┌─────────────────────────────────────────────────┐
│  Security Layers                                 │
├─────────────────────────────────────────────────┤
│  1. API Authentication                           │
│     • Fitbit: OAuth 2.0 with refresh tokens     │
│     • Azure: SAS tokens with device identity    │
│                                                  │
│  2. Transport Security                           │
│     • TLS 1.2+ for all connections              │
│     • Certificate validation                     │
│                                                  │
│  3. Data Protection                              │
│     • Credentials in .env (not in code)         │
│     • .gitignore prevents credential leaks      │
│     • Local storage only on trusted devices     │
│                                                  │
│  4. Azure IoT Security                           │
│     • Device authentication                      │
│     • Per-device access keys                    │
│     • Message encryption                         │
│     • Access policy isolation                    │
└─────────────────────────────────────────────────┘
```

## Scalability Considerations

### Current Architecture (Single User)
- One Fitbit account → One Data Ferry → One IoT Hub → One Raspberry Pi

### Future Multi-User Architecture
```
Multiple Users
    ├─ User 1 → Data Ferry 1 ─┐
    ├─ User 2 → Data Ferry 2 ─┤
    └─ User 3 → Data Ferry 3 ─┼→ Shared IoT Hub → Multiple Devices
                               │    ├─ Device 1 (User 1's Pi)
                               │    ├─ Device 2 (User 2's Pi)
                               │    └─ Device 3 (User 3's Pi)
```

### Optimization Strategies
1. **Batch Processing**: Collect data from multiple users in parallel
2. **Event Hub**: For high-throughput scenarios (100+ devices)
3. **Edge AI**: Run more complex models on Pi 5's neural processing
4. **Cloud Functions**: Deploy Data Ferry as actual Azure Function
5. **Cosmos DB**: Store historical sleep data for ML training

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Data Source** | Fitbit Web API | Sleep, HR, HRV data |
| **Cloud Messaging** | Azure IoT Hub | Device communication |
| **Cloud SDK** | azure-iot-hub | Service-side messaging |
| **Edge SDK** | azure-iot-device | Device client |
| **API Client** | python-fitbit | Fitbit data access |
| **AI/ML** | NumPy | Numerical analysis |
| **Hardware** | RPi.GPIO | Raspberry Pi control |
| **Language** | Python 3.8+ | All components |

## Performance Metrics

### Expected Latencies
- Fitbit API call: 500-2000ms
- IoT Hub message delivery: 100-500ms
- AI analysis: 50-200ms
- Total pipeline: ~3-5 seconds

### Resource Usage (Raspberry Pi 5)
- CPU: < 5% idle, ~20% during analysis
- Memory: ~50MB Python process
- Network: ~10KB per data transmission
- Storage: Minimal (logs only)

### Reliability
- Fitbit API: 99.9% uptime
- Azure IoT Hub: 99.9% SLA
- Raspberry Pi: Depends on power/network
- **Fallback**: Traditional timer if data unavailable

---

**Last Updated**: November 27, 2025
