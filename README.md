# Smart Sleep Alarm System (Java Edition)

A complete IoT-based smart alarm system that uses AI to determine the optimal wake-up time based on your sleep cycle data. Now re-engineered in Java with a festive Christmas-themed UI!

## Architecture

The system has been migrated to a robust Java microservices architecture:

### 1. **Cloud Service** (`smart-alarm-cloud`)
- **Technology**: Spring Boot 3.2, Redis
- **Function**:
  - REST API for data ingestion.
  - Cloud-based AI model analysis.
  - Data persistence using Redis.
- **Endpoints**:
  - `POST /api/sleep/analyze`: Analyzes sleep patterns.

### 2. **Edge Service** (`smart-alarm-edge`)
- **Technology**: Java 17, JavaFX 21
- **Function**:
  - Runs on Raspberry Pi (or any desktop).
  - Beautiful Christmas-themed Dashboard.
  - Local AI Model for real-time wake-up decisions (Edge Computing).
  - Syncs data with the Cloud Service.

### 3. **Shared Library** (`smart-alarm-shared`)
- Common Data Transfer Objects (DTOs) and utilities.

## Data Flow

```
Sensors/Fitbit -> Edge Service (JavaFX) -> Local AI -> Wake Up Signal
                          |
                          v
                     Cloud Service (Spring Boot) -> Redis DB
```

## Getting Started

### Prerequisites
- Java JDK 17 or higher
- Maven 3.8+
- Redis Server (for Cloud Service)

### Building the Project

```powershell
mvn clean install
```

### Running the Cloud Service

```powershell
cd smart-alarm-cloud
mvn spring-boot:run
```

### Running the Edge Service (UI)

```powershell
cd smart-alarm-edge
mvn javafx:run
```

## Features
- **Dual-Model AI**: Local inference for low latency, Cloud inference for deep analysis.
- **Festive UI**: A custom-styled JavaFX interface with a cozy Christmas theme.
- **Scalable**: Microservices ready architecture.
