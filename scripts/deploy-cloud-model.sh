#!/bin/bash

echo "Deploying Smart Alarm Cloud Model to Azure..."

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP}"
ACR_NAME="smartalarmregistry"
APP_NAME="smart-alarm-model"
IMAGE_NAME="smart-alarm-model"

echo "Building and pushing Docker image..."
cd backend/python-model-service
python train_model.py
docker build -t ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest .
docker push ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest

echo "Deploying to Azure Container App..."
az containerapp update \
  --name ${APP_NAME} \
  --resource-group ${RESOURCE_GROUP} \
  --image ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest

echo "Deployment complete!"
echo "Model URL: https://${APP_NAME}.azurewebsites.net/predict"
