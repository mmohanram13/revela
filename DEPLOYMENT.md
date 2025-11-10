# Cloud Run Deployment Guide

This guide explains how to deploy Revela to Google Cloud Run using source-based deployment.

## Architecture Overview

Revela uses a simple Cloud Run architecture:

1. **Backend API Service** (CPU) - Handles session management, DuckDB analytics, and LLM orchestration
2. **Ollama Service** (Optional GPU) - Can be deployed separately for GPU-accelerated inference or use a local/external Ollama instance

## Prerequisites

- Google Cloud Platform account
- `gcloud` CLI installed and configured
- Enable the following APIs:
  - Cloud Run API
  - Cloud Build API (used automatically by source deploy)

## Setup Instructions

### 1. Set Up GCP Project

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 2. Deploy Ollama Service (Optional - if you want GPU inference)

If you have a separate Ollama service already running (e.g., locally or on another Cloud Run instance):

```bash
# Example: Deploy Ollama to Cloud Run with GPU
cd ollama-gemma
gcloud run deploy revela-ollama \
  --source . \
  --region europe-west4 \
  --platform managed \
  --no-allow-unauthenticated \
  --cpu 4 \
  --memory 8Gi \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --timeout 600 \
  --max-instances 5 \
  --min-instances 0

# Get the Ollama service URL
export OLLAMA_HOST=$(gcloud run services describe revela-ollama \
  --region europe-west4 \
  --format='value(status.url)')

echo "Ollama Service URL: $OLLAMA_HOST"
```

**Note**: GPU instances may have limited availability. If deployment fails, try a different region:
- `europe-west4`
- `us-central1`
- `us-west1`

Or use a local Ollama instance: `export OLLAMA_HOST=http://localhost:11434`

### 3. Deploy Backend Service

From the `revela-app` directory:

```bash
cd revela-app

# Deploy using source-based deployment
gcloud run deploy revela-app \
  --source . \
  --region europe-west4 \
  --platform managed \
  --allow-unauthenticated \
  --cpu 2 \
  --memory 2Gi \
  --timeout 300 \
  --max-instances 1 \
  --min-instances 0 \
  --set-env-vars OLLAMA_HOST=${OLLAMA_HOST:-http://localhost:11434}

# Get the backend service URL
export BACKEND_URL=$(gcloud run services describe revela-app \
  --region europe-west4 \
  --format='value(status.url)')

echo "Backend Service URL: $BACKEND_URL"
```

### 4. Configure IAM Permissions (if using private Ollama service)

If your Ollama service is private (recommended), allow the backend service to invoke it:

```bash
# Get backend service account
export BACKEND_SA=$(gcloud run services describe revela-app \
  --region europe-west4 \
  --format='value(spec.template.spec.serviceAccountName)')

# Grant invoker permission
gcloud run services add-iam-policy-binding revela-ollama \
  --region europe-west4 \
  --member="serviceAccount:$BACKEND_SA" \
  --role="roles/run.invoker"
```

### 5. Update Chrome Extension

Update the extension's `content.js` to point to your Cloud Run backend:

```javascript
// In chrome-extension/src/content/content.js
const API_ENDPOINT = 'YOUR_BACKEND_URL'; // Replace with $BACKEND_URL
```

## Local Testing Before Deployment

### Test Backend Locally

```bash
cd revela-app

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv add --all

# Run locally
./start-app.sh

# Or run with gunicorn directly
uv run gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --reload src.app:app

# Test health endpoint
curl http://localhost:8080/health
```

### Test with Docker (Optional)

```bash
cd revela-app

# Build Docker image
docker build -t revela-backend .

# Run container
docker run -p 8080:8080 \
  -e ENVIRONMENT=development \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  revela-backend

# Test health endpoint
curl http://localhost:8080/health
```

## Environment Variables

### Backend Service

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Runtime environment | `production` | No |
| `OLLAMA_HOST` | Ollama service URL | `http://localhost:11434` | Yes |
| `PORT` | Server port | `8080` | No |

Set during deployment:
```bash
--set-env-vars OLLAMA_HOST=https://your-ollama-service.run.app
```

## Monitoring and Logging

### View Logs

```bash
# Backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=revela-app" \
  --limit 50 \
  --format json

# Stream logs in real-time
gcloud run services logs tail revela-app --region europe-west4
```

### Monitor Metrics

```bash
# Service details
gcloud run services describe revela-app \
  --region europe-west4 \
  --format='get(status)'

# Get service URL
gcloud run services describe revela-app \
  --region europe-west4 \
  --format='get(status.url)'
```

## Scaling Configuration

### Backend (CPU)
- **Min instances**: 0 (scales to zero)
- **Max instances**: 1 (configurable)
- **Concurrency**: 80 requests per instance (default)
- **Memory**: 2 GiB
- **CPU**: 2 vCPUs
- **Timeout**: 300 seconds

Configure scaling:
```bash
gcloud run services update revela-app \
  --region europe-west4 \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80
```

## Cost Optimization

1. **Session Timeout**: Sessions auto-expire after 30 minutes to free resources
2. **Scale to Zero**: Both services scale to zero during inactivity
3. **Warm-up**: Consider setting `min-instances=1` for inference service to avoid cold starts
4. **GPU Selection**: L4 GPUs offer good price/performance for Gemma models

## Troubleshooting

### Cold Start Issues

First request after idle period can take 2-5 seconds. To mitigate:

```bash
# Set minimum instances to 1 (always warm)
gcloud run services update revela-app \
  --region europe-west4 \
  --min-instances 1
```

### Memory Issues

If experiencing OOM errors:

```bash
# Increase memory
gcloud run services update revela-app \
  --region europe-west4 \
  --memory 4Gi
```

### Connection Timeouts

Increase timeout for long-running requests:

```bash
gcloud run services update revela-app \
  --region europe-west4 \
  --timeout 600
```

### Ollama Connection Issues

Check the OLLAMA_HOST environment variable:

```bash
# View current environment variables
gcloud run services describe revela-app \
  --region europe-west4 \
  --format='get(spec.template.spec.containers[0].env)'

# Update OLLAMA_HOST
gcloud run services update revela-app \
  --region europe-west4 \
  --set-env-vars OLLAMA_HOST=https://your-ollama-service.run.app
```

## Updating Services

### Deploy New Version

Source-based deployment automatically builds and deploys:

```bash
cd revela-app

# Deploy new version
gcloud run deploy revela-app \
  --source . \
  --region europe-west4

# Or with specific configuration updates
gcloud run deploy revela-app \
  --source . \
  --region europe-west4 \
  --memory 4Gi \
  --cpu 4
```

### Rollback to Previous Revision

```bash
# List revisions
gcloud run revisions list \
  --service revela-app \
  --region europe-west4

# Rollback to specific revision
gcloud run services update-traffic revela-app \
  --region europe-west4 \
  --to-revisions REVISION_NAME=100
```

## Security Best Practices

1. **Private Ollama Service**: Set Ollama service to not allow unauthenticated access
2. **Service-to-Service Auth**: Backend authenticates to Ollama using service accounts
3. **HTTPS Only**: All traffic encrypted via Cloud Run's managed certificates
4. **No Persistent Storage**: All data ephemeral, destroyed after session timeout
5. **CORS Configuration**: Restrict origins to your extension ID in production

### Making Ollama Service Private

```bash
# Remove public access
gcloud run services update revela-ollama \
  --region europe-west4 \
  --no-allow-unauthenticated

# Then grant backend service access (see step 4 above)
```

## Support

For issues or questions:
- Check Cloud Run logs: `gcloud logging read`
- Monitor quotas: `gcloud compute project-info describe`
- GPU availability: Check [Cloud Run GPU documentation](https://cloud.google.com/run/docs/configuring/services/gpu)
