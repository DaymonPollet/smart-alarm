# Kubernetes Deployment for Smart Alarm

This directory contains Kubernetes manifests for deploying the Smart Alarm application to a Raspberry Pi running k3s.

##  Structure

```
k8s/
├── base/                        # Base configurations
│   ├── namespace.yaml           # smart-alarm namespace
│   ├── configmap.yaml           # Application configuration
│   ├── secrets.yaml.template    # Template for secrets
│   ├── storage.yaml             # PersistentVolumes & PVCs
│   ├── backend-deployment.yaml  # Backend deployment
│   ├── backend-service.yaml     # Backend services (ClusterIP)
│   ├── frontend-deployment.yaml # Frontend deployment
│   ├── frontend-service.yaml    # Frontend service (NodePort 30080)
│   ├── ingress.yaml             # Nginx ingress
│   └── kustomization.yaml       # Kustomize configuration
├── canary/                      # Canary deployment overlay
│   ├── backend-canary.yaml      # Canary backend deployment
│   ├── frontend-canary.yaml     # Canary frontend deployment
│   ├── traffic-split.yaml       # Canary traffic routing (20%)
│   └── kustomization.yaml       # Canary kustomization
└── README.md
```

## Quick Start

### Prerequisites

1. **Raspberry Pi** with k3s installed
2. **kubectl** configured to access the cluster
3. **Docker Hub** account for container images
4. **GitHub Secrets** configured for CI/CD

### Local Deployment (Manual)

```bash
# From the project root on your Raspberry Pi

# 1. Full deployment (first time)
./scripts/deploy-local.sh full

# 2. Check status
./scripts/deploy-local.sh status

# 3. Deploy canary (for updates)
CANARY_TAG=v2.0.0 ./scripts/deploy-local.sh canary

# 4. Promote canary to stable
./scripts/deploy-local.sh promote

# Or rollback if issues
./scripts/deploy-local.sh rollback
```

### CI/CD Deployment (GitHub Actions)

The deployment is automated via GitHub Actions:

1. **Push to main** → Triggers build & deploy
2. **Manual workflow** → Choose deployment type

```yaml
# Trigger manually from GitHub Actions tab
# Options: full, canary, rollback, promote
```

## Secrets Management

### Option 1: Generate from environment variables

```bash
# Set environment variables
export FITBIT_CLIENT_ID="your-client-id"
export FITBIT_CLIENT_SECRET="your-client-secret"
export AZURE_STORAGE_CONNECTION_STRING="your-connection-string"
export AZURE_ML_ENDPOINT="your-ml-endpoint"
export AZURE_ML_API_KEY="your-api-key"

# Generate secrets file
./scripts/generate-secrets.sh > k8s/base/secrets.yaml

# Apply to cluster
kubectl apply -f k8s/base/secrets.yaml
```

### Option 2: Create manually

```bash
kubectl create secret generic smart-alarm-secrets \
  --namespace=smart-alarm \
  --from-literal=FITBIT_CLIENT_ID="xxx" \
  --from-literal=FITBIT_CLIENT_SECRET="xxx" \
  --from-literal=AZURE_STORAGE_CONNECTION_STRING="xxx" \
  --from-literal=AZURE_IOT_CONNECTION_STRING="" \
  --from-literal=AZURE_ML_ENDPOINT="xxx" \
  --from-literal=AZURE_ML_API_KEY="xxx"
```

### Option 3: GitHub Secrets (for CI/CD)

Required secrets in GitHub repository settings:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `FITBIT_CLIENT_ID`
- `FITBIT_CLIENT_SECRET`
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_ML_ENDPOINT`
- `AZURE_ML_API_KEY`

## Deployment Strategies

### Full Deployment
Deploys the entire application from scratch. Use for:
- First-time deployment
- Complete reinstallation
- Disaster recovery

```bash
./scripts/deploy-local.sh full
# or via GitHub Actions with "full" type
```

### Canary Deployment
Deploys new version alongside stable with 20% traffic. Use for:
- Testing new features
- Gradual rollout
- A/B testing

```bash
CANARY_TAG=v2.0.0 ./scripts/deploy-local.sh canary
# or via GitHub Actions with "canary" type
```

### Traffic Flow

```
┌─────────────────────────────────────────────────┐
│                   Ingress                        │
│              (smart-alarm.local)                 │
└────────────────────┬────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │ 80%                   │ 20%
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ Stable Service  │    │ Canary Service  │
│   (backend)     │    │(backend-canary) │
└─────────────────┘    └─────────────────┘
```

##s Storage

### Local Storage (hostPath)
Data persisted on the Raspberry Pi at `/data/smart-alarm/`:

```
/data/smart-alarm/
├── data/           # SQLite database, user data
│   └── smart_alarm.db
└── model/          # ML model files
    └── model.joblib
```

### Azure Blob Storage
For cloud backup and sync:
- Predictions synced to `predictions` container
- Logs synced to `logs` container
- Configured via `AZURE_STORAGE_CONNECTION_STRING`

## Monitoring & Debugging

### Check Deployment Status

```bash
# All resources
kubectl get all -n smart-alarm

# Pods
kubectl get pods -n smart-alarm -o wide

# Services
kubectl get svc -n smart-alarm
```

### View Logs

```bash
# Backend logs
kubectl logs -n smart-alarm -l app=smart-alarm-backend -f

# Frontend logs
kubectl logs -n smart-alarm -l app=smart-alarm-frontend -f

# Canary logs
kubectl logs -n smart-alarm -l version=canary -f
```

### Health Checks

```bash
# Backend health
kubectl exec -n smart-alarm deployment/smart-alarm-backend -- curl -s http://localhost:8080/health

# Port forward for local testing
kubectl port-forward -n smart-alarm svc/smart-alarm-frontend 8080:80
```

### Debugging Issues

```bash
# Describe pod for events
kubectl describe pod -n smart-alarm -l app=smart-alarm-backend

# Get pod shell
kubectl exec -it -n smart-alarm deployment/smart-alarm-backend -- /bin/sh

# Check PV/PVC status
kubectl get pv,pvc -n smart-alarm
```

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | `http://<PI-IP>:30080` | React dashboard |
| Backend API | `http://<PI-IP>:30080/api` | REST API |
| Health Check | `http://<PI-IP>:30080/api/health` | Health endpoint |
| Ingress | `http://smart-alarm.local` | Domain-based (requires DNS) |

## Customization

### Change Resource Limits

Edit `backend-deployment.yaml` or `frontend-deployment.yaml`:

```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Change Canary Traffic Weight

Edit `canary/traffic-split.yaml`:

```yaml
annotations:
  nginx.ingress.kubernetes.io/canary-weight: "20"  # Change to desired %
```

### Add Custom Configuration

Edit `base/configmap.yaml`:

```yaml
data:
  MY_CUSTOM_VAR: "value"
```

## Cleanup

```bash
# Remove entire deployment
kubectl delete namespace smart-alarm

# Remove canary only
./scripts/deploy-local.sh rollback

# Remove specific resources
kubectl delete deployment smart-alarm-backend -n smart-alarm
```
