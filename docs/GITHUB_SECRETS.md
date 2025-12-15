# GitHub Secrets Configuration

## Required Secrets

Set these in: **GitHub Repository → Settings → Secrets and variables → Actions → New repository secret**

### 1. Azure Secrets

```
AZURE_CREDENTIALS
```
Value: JSON from Azure service principal creation (see AZURE_SETUP.md)
```json
{
  "clientId": "<client-id>",
  "clientSecret": "<client-secret>",
  "subscriptionId": "<subscription-id>",
  "tenantId": "<tenant-id>",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  ...
}
```

```
AZURE_RESOURCE_GROUP
```
Value: Your Azure resource group name (e.g., `smart-alarm-rg`)

```
CLOUD_MODEL_URL
```
Value: Azure Container App URL (e.g., `https://smart-alarm-model.northeurope.azurecontainerapps.io/predict`)

### 2. IoT Hub Secrets

```
IOTHUB_CONNECTION_STRING
```
Value:
```
HostName=<your-hub>.azure-devices.net;DeviceId=<device-id>;SharedAccessKey=<your-key>
```

### 3. Fitbit Secrets

```
FITBIT_CLIENT_ID
```
Value: `23TMGB`

```
FITBIT_CLIENT_SECRET
```
Value: `577ff9a33b4dfa2f8b4e7f631028999f`

```
FITBIT_ACCESS_TOKEN
```
Value: Obtained from OAuth flow (see FITBIT_SETUP.md)
Example: `eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyM1RNR0IiLCJzdWIiOiI5...`

```
FITBIT_REFRESH_TOKEN
```
Value: Obtained from OAuth flow
Example: `abc123def456ghi789jkl012mno345pqr678stu901vwx234yz`

### 4. Database Secrets

```
QUEST_DB_USER
```
Value: `admin`

```
QUEST_DB_PASSWORD
```
Value: `Admin.1234`

### 5. Docker Secrets

```
DOCKER_USERNAME
```
Value: `daymonpollet`

```
DOCKER_TOKEN
```
Value: `<your-docker-token>`

## Verification

After setting all secrets, you should have **12 secrets** total:

1. AZURE_CREDENTIALS
2. AZURE_RESOURCE_GROUP
3. CLOUD_MODEL_URL
4. IOTHUB_CONNECTION_STRING
5. FITBIT_CLIENT_ID
6. FITBIT_CLIENT_SECRET
7. FITBIT_ACCESS_TOKEN
8. FITBIT_REFRESH_TOKEN
9. QUEST_DB_USER
10. QUEST_DB_PASSWORD
11. DOCKER_USERNAME
12. DOCKER_TOKEN

## Security Notes

- Never commit secrets to Git
- Rotate tokens periodically
- Use GitHub environment secrets for production vs. staging
- Enable secret scanning in repository settings
