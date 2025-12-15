# What You Need To Do

## 1. Fitbit API - Get Access Token

**Action Required**: Authorize your Fitbit app to get tokens

1. Start the API server locally:
```bash
cd edge
pip install -r requirements.txt
python api.py
```

2. Open this URL in your browser:
```
https://www.fitbit.com/oauth2/authorize?response_type=code&client_id=23TMGB&redirect_uri=http%3A%2F%2F127.0.0.1%3A8080%2Fapi%2Foauth%2Fcallback&scope=activity%20heartrate%20location%20nutrition%20profile%20settings%20sleep%20social%20weight&expires_in=604800
```

3. Login and authorize

4. The tokens will be automatically saved to `edge/.env`

5. Copy the tokens and add to GitHub Secrets

## 2. Azure - Deploy Cloud Model

**Action Required**: Create Azure Container App for the cloud model

```bash
az login

az containerapp env create \
  --name smart-alarm-env \
  --resource-group <YOUR_RESOURCE_GROUP> \
  --location northeurope

az acr create \
  --resource-group <YOUR_RESOURCE_GROUP> \
  --name smartalarmregistry \
  --sku Basic

az acr login --name smartalarmregistry

cd backend/python-model-service
python train_model.py

az acr build \
  --registry smartalarmregistry \
  --image smart-alarm-model:latest \
  .

az containerapp create \
  --name smart-alarm-model \
  --resource-group <YOUR_RESOURCE_GROUP> \
  --environment smart-alarm-env \
  --image smartalarmregistry.azurecr.io/smart-alarm-model:latest \
  --target-port 5000 \
  --ingress external \
  --min-replicas 1

az containerapp show \
  --name smart-alarm-model \
  --resource-group <YOUR_RESOURCE_GROUP> \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

Save the output URL as GitHub Secret `CLOUD_MODEL_URL` with format:
```
https://<output-from-above>/predict
```

## 3. Azure - Create Service Principal for GitHub Actions

```bash
az ad sp create-for-rbac \
  --name "smart-alarm-github" \
  --role contributor \
  --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/<YOUR_RESOURCE_GROUP> \
  --sdk-auth
```

Copy the JSON output and save as GitHub Secret `AZURE_CREDENTIALS`

## 4. GitHub Secrets - Set All Required Secrets

Go to: **GitHub Repo → Settings → Secrets and variables → Actions**

Add these secrets (see `docs/GITHUB_SECRETS.md` for details):

**Already have values for**:
- IOTHUB_CONNECTION_STRING
- FITBIT_CLIENT_ID
- FITBIT_CLIENT_SECRET
- QUEST_DB_USER
- QUEST_DB_PASSWORD
- DOCKER_USERNAME
- DOCKER_TOKEN

**Need to add**:
- FITBIT_ACCESS_TOKEN (from step 1)
- FITBIT_REFRESH_TOKEN (from step 1)
- CLOUD_MODEL_URL (from step 2)
- AZURE_CREDENTIALS (from step 3)
- AZURE_RESOURCE_GROUP (your resource group name)

## 5. Raspberry Pi - Setup Self-Hosted Runner

**Action Required**: Install GitHub Actions runner on your Pi

1. SSH into your Raspberry Pi

2. Go to: **GitHub Repo → Settings → Actions → Runners → New self-hosted runner**

3. Select **Linux** and **ARM64**

4. Follow the installation commands shown:
```bash
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-arm64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-arm64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-arm64-2.311.0.tar.gz
./config.sh --url https://github.com/<your-username>/<your-repo> --token <token-from-github>
./run.sh
```

5. Install as service (optional):
```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

## 6. Local Testing - Before Pushing

**Action Required**: Test everything locally first

```bash
cd edge
cp .env.example .env

docker-compose -f ../docker-compose-local.yml up -d

pip install -r requirements.txt

python api.py &

python main.py &

cd ../frontend
npm install
npm start
```

Visit `http://localhost:3000` to see the dashboard

## 7. Deploy - Push to GitHub

```bash
git add .
git commit -m "Deploy smart alarm system"
git push origin main
```

This will trigger GitHub Actions to deploy everything automatically.

## Model Training Note

The dataset contains features not available from Fitbit API (accelerometer data). The model has been updated to only use:
- Mean Heart Rate
- Std Heart Rate
- Min Heart Rate
- Max Heart Rate
- HRV (RMSSD)

These are all available from Fitbit's heart rate API.

## Summary

**Two models, same algorithm, different locations**:

1. **Local Model (Raspberry Pi)**:
   - Runs in Docker container
   - Purpose: Fast, offline predictions for immediate alarm decisions
   - Demonstrates: Edge Computing

2. **Cloud Model (Azure)**:
   - Runs in Azure Container App
   - Purpose: Accessible from anywhere, can be scaled, backup
   - Demonstrates: Cloud Computing

Both use Random Forest trained on the same sleep stage dataset with Fitbit-compatible features.
