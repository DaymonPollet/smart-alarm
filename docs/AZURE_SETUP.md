# Azure Configuration Steps

## 1. Create Azure Container Registry

```bash
az acr create \
  --resource-group <your-resource-group> \
  --name smartalarmregistry \
  --sku Basic \
  --location northeurope

az acr login --name smartalarmregistry
```

## 2. Create Azure Container Apps Environment

```bash
az containerapp env create \
  --name smart-alarm-env \
  --resource-group <your-resource-group> \
  --location northeurope
```

## 3. Deploy Cloud Model

```bash
az acr build \
  --registry smartalarmregistry \
  --image smart-alarm-model:latest \
  ./backend/python-model-service

az containerapp create \
  --name smart-alarm-model \
  --resource-group <your-resource-group> \
  --environment smart-alarm-env \
  --image smartalarmregistry.azurecr.io/smart-alarm-model:latest \
  --target-port 5000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3
```

## 4. Get Cloud Model URL

```bash
az containerapp show \
  --name smart-alarm-model \
  --resource-group <your-resource-group> \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

Save this URL as `CLOUD_MODEL_URL` in GitHub Secrets with format:
```
https://<fqdn>/predict
```

## 5. Azure Service Principal for GitHub Actions

```bash
az ad sp create-for-rbac \
  --name "smart-alarm-github-actions" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group> \
  --sdk-auth
```

Copy the JSON output and save as GitHub Secret `AZURE_CREDENTIALS`

## 6. IoT Hub Configuration (Already Done)

Your existing IoT Hub:
- Name: `HowestTICCFAIDaymon`
- Device: `RPISmartHome`
- Connection string is already in your env file

To verify:
```bash
az iot hub device-identity show \
  --hub-name HowestTICCFAIDaymon \
  --device-id RPISmartHome
```

## 7. GitHub Secrets to Set

Go to GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these:
```
AZURE_CREDENTIALS=<JSON from step 5>
AZURE_RESOURCE_GROUP=<your-resource-group-name>
CLOUD_MODEL_URL=https://<container-app-fqdn>/predict
```

All other secrets are already provided in your env file.
