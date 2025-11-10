# Building Revela: Gemma-3 Powered Data Analysis Chrome Extension with Google Cloud Run

**This article was created for the purposes of entering the Google Cloud Run Hackathon on Devpost.**

## Introduction

Imagine browsing through Wikipedia, reading a financial report, or exploring research data online, and being able to instantly analyze any table or chart with the power of AI — without leaving the page. That's exactly what Revela does.

Revela is a Chrome extension that brings AI-powered data analysis directly to your browser. It combines the serverless capabilities of Google Cloud Run with Google's Gemma 3 language model to provide ephemeral, privacy-first analysis of data visualizations on any webpage.

In this tutorial, I'll walk you through how I built Revela from the ground up, leveraging Cloud Run's unique features like GPU support, auto-scaling, and source-based deployments to create a production-ready application.

## What is Revela?

Revela is a "Data Copilot for the Web" that enables users to:

- Hover over any table or chart to see instant AI-generated insights
- Start conversational analysis through an interactive chat interface
- Generate visualizations automatically using matplotlib
- Ask complex questions about web data and get immediate answers
- Analyze existing charts and images using vision AI

All of this happens with zero setup, complete privacy (ephemeral sessions with no persistent storage), and works on any public webpage.

## Architecture Overview

Revela consists of three main components:

**1. Chrome Extension (Frontend)**
- Detects tables and images on web pages
- Provides hover icons and chat interface
- Manages user sessions
- Extracts and sends data to the backend

**2. Backend API Service (Flask on Cloud Run - CPU)**
- Manages ephemeral sessions with 30-minute timeout
- Processes HTML tables and images
- Orchestrates LLM queries
- Executes Polars-based data queries
- Generates matplotlib charts
- Resources: 2 vCPU, 2 GiB RAM, scales 0-10 instances

**3. Ollama LLM Container (Cloud Run - GPU)**
- Hosts Gemma 3 (12B parameter) model
- Handles vision analysis for charts
- Processes natural language queries
- GPU-accelerated inference with NVIDIA L4
- Resources: 4 vCPU, 8 GiB RAM, 1x NVIDIA L4 GPU, scales 0-5 instances

```
┌─────────────────────┐
│  Chrome Extension   │  Browser-side detection and UI
└──────────┬──────────┘
           │ HTTPS/JSON
           ▼
┌─────────────────────┐
│   Backend API       │  Flask service on Cloud Run (CPU)
│   (revela-app)      │  - Session management
│                     │  - Data processing (Polars)
│   - Session Mgmt    │  - Chart generation
│   - Polars queries  │  - LLM orchestration
│   - Chart gen       │
└──────────┬──────────┘
           │ Internal HTTPS
           ▼
┌─────────────────────┐
│  Ollama Service     │  LLM inference on Cloud Run (GPU)
│  (ollama-gemma)     │  - Gemma 3 model
│                     │  - Vision analysis
│   - Gemma 3 12B     │  - Natural language processing
│   - GPU inference   │
└─────────────────────┘
```

## Why Google Cloud Run?

Cloud Run was the perfect choice for Revela for several key reasons:

**1. GPU Support**
Cloud Run's native GPU support (NVIDIA L4) enabled me to run the resource-intensive Gemma 3 12B model efficiently. This is crucial for providing fast AI inference while keeping costs manageable.

**2. Auto-scaling to Zero**
Since Revela is designed for ephemeral analysis sessions, Cloud Run's ability to scale to zero when idle means I only pay for actual usage. This is perfect for a hackathon project that might have sporadic traffic.

**3. Source-based Deployment**
Cloud Run can deploy directly from source code, eliminating the need to manage Docker registries. This simplified my CI/CD pipeline significantly.

**4. Service-to-Service Authentication**
Built-in IAM authentication made it easy to secure communication between the Flask backend and the Ollama service without managing additional secrets.

**5. Serverless Simplicity**
No infrastructure management means I could focus entirely on building features rather than managing servers, load balancers, or autoscaling configurations.

## Step-by-Step Cloud Run Deployment Guide

### Prerequisites

Before we begin, ensure you have:

- Google Cloud Platform account with billing enabled
- gcloud CLI installed and configured (`gcloud init`)
- Basic understanding of Docker and containerization

### Project Overview

Revela consists of:
- **Chrome Extension**: Detects tables/charts on web pages (runs in browser)
- **Flask Backend**: API service for session management and data processing
- **Ollama Service**: GPU-accelerated LLM inference with Gemma 3 12B

We'll deploy the two backend services to Cloud Run, leveraging both CPU and GPU instances.

### Step 1: Deploying the Ollama LLM Service with GPU

The first service hosts the Gemma 3 language model with GPU acceleration.

**File: `ollama-gemma/Dockerfile`**

```dockerfile
FROM ollama/ollama:latest

ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_KEEP_ALIVE=30m

RUN echo '#!/bin/bash\n\
ollama serve &\n\
OLLAMA_PID=$!\n\
sleep 10\n\
ollama pull gemma3:12b-it-qat\n\
wait $OLLAMA_PID' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]
```

This Dockerfile pulls and serves the Gemma 3 model (12B parameters, quantized for efficiency).

### Step 2: Preparing the Flask Backend

The Flask backend handles API requests, manages sessions, and communicates with the Ollama service. The key requirement is service-to-service authentication.

**File: `revela-app/src/config_module.py`** (Authentication logic)

```python
import os
import google.auth.transport.requests
import google.oauth2.id_token

class Config:
    def get_headers(self) -> dict:
        """Get headers with automatic Cloud Run authentication."""
        headers = {"Content-Type": "application/json"}
        
        if os.getenv("ENVIRONMENT") == "production":
            # Fetch ID token for service-to-service auth
            auth_req = google.auth.transport.requests.Request()
            id_token = google.oauth2.id_token.fetch_id_token(
                auth_req, 
                os.getenv("OLLAMA_HOST")  # Target service URL
            )
            headers["Authorization"] = f"Bearer {id_token}"
        
        return headers
```

This automatically adds authentication tokens when calling the Ollama service in production.

**File: `revela-app/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY src/ ./src/
COPY ui/ ./ui/

RUN uv pip install --system --no-cache .

ENV ENVIRONMENT=production
EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "src.app:app"]
```

The backend uses Flask for the API, Polars for data processing, and matplotlib for chart generation. The complete implementation handles session management, table extraction, and LLM orchestration.

### Step 3: Deploying the Flask Backend to Cloud Run

First, capture the Ollama service URL:

```bash
OLLAMA_URL=$(gcloud run services describe ollama-gemma \
  --region=europe-west4 \
  --format='value(status.url)')

echo "Ollama URL: $OLLAMA_URL"
```

Deploy the backend:

### Step 5: Deploying to Google Cloud Run

Now comes the exciting part — deploying to Cloud Run!

**Deploy to Cloud Run with GPU:**

```bash
cd ollama-gemma

gcloud run deploy ollama-gemma \
  --source . \
  --region=europe-west4 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=8Gi \
  --cpu=4 \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --port=11434 \
  --min-instances=0 \
  --max-instances=5 \
  --timeout=300 \
  --set-env-vars=OLLAMA_KEEP_ALIVE=30m
```

**Detailed Parameter Breakdown:**

**Service Identification:**
- `ollama-gemma`: The name of your Cloud Run service. This will be used in the service URL and for subsequent management commands.

**Deployment Source:**
- `--source .`: Deploys directly from the current directory's source code. Cloud Run automatically builds the Docker image using Cloud Build, eliminating the need to manually build and push images to a registry. This is one of Cloud Run's most developer-friendly features.

**Regional Configuration:**
- `--region=europe-west4`: Specifies the Google Cloud region (Netherlands). Choose a region close to your users for lower latency. GPU availability varies by region, so ensure your chosen region supports NVIDIA L4 GPUs.
- `--platform=managed`: Uses fully managed Cloud Run (as opposed to Cloud Run for Anthos). Google handles all infrastructure, scaling, and availability.

**Network Access:**
- `--allow-unauthenticated`: Allows public access without authentication. For production, consider using `--no-allow-unauthenticated` and implementing proper authentication via IAM or API keys.

**Resource Allocation:**
- `--memory=8Gi`: Allocates 8 GiB of RAM. The Gemma 3 12B model requires substantial memory for loading model weights and maintaining inference state. Each request also needs memory for context and generation.
- `--cpu=4`: Allocates 4 vCPUs. While the GPU handles inference, CPUs are needed for request handling, data preprocessing, and managing the Ollama service.
- `--gpu=1`: Provisions one GPU unit for hardware-accelerated inference.
- `--gpu-type=nvidia-l4`: Specifies the NVIDIA L4 GPU, which offers excellent price-performance for AI inference. L4 provides 24GB VRAM and is optimized for transformer models like Gemma.

**Network Configuration:**
- `--port=11434`: The container port where Ollama listens. Cloud Run routes HTTPS traffic (443) to this internal port. Must match the `EXPOSE` directive in your Dockerfile.

**Scaling Behavior:**
- `--min-instances=0`: Scales down to zero instances when idle, minimizing costs. The first request after scaling to zero will experience a cold start (typically 30-60 seconds for GPU services as the model loads).
- `--max-instances=5`: Limits maximum concurrent instances to 5. This prevents runaway costs and ensures you don't exceed quota limits. Each instance can handle multiple concurrent requests up to the `--concurrency` limit (default: 80).

**Request Handling:**
- `--timeout=300`: Sets the maximum request duration to 300 seconds (5 minutes). LLM inference can take time, especially for complex prompts or long responses. The default is 300s; maximum allowed is 3600s.

**Environment Variables:**
- `--set-env-vars=OLLAMA_KEEP_ALIVE=30m`: Sets environment variables in the container. `OLLAMA_KEEP_ALIVE=30m` tells Ollama to keep the model loaded in memory for 30 minutes after the last request, reducing latency for subsequent requests within that window.

Wait for deployment to complete (typically 3-5 minutes for first deployment). Save the service URL displayed.

### Step 2: Preparing the Flask Backend

```bash
# Get the Ollama service URL
OLLAMA_URL=$(gcloud run services describe ollama-gemma \
  --region=europe-west4 \
  --format='value(status.url)')

echo "Ollama URL: $OLLAMA_URL"
```

**Command Breakdown:**

- `gcloud run services describe`: Retrieves detailed information about a deployed Cloud Run service
- `ollama-gemma`: The service name we just deployed
- `--region=europe-west4`: Must match the deployment region
- `--format='value(status.url)'`: Extracts only the service URL from the output. The `status.url` field contains the fully qualified HTTPS endpoint for the service
- `$()`: Bash command substitution to store the URL in the `OLLAMA_URL` variable

This URL will be used as an environment variable in the backend service, enabling it to communicate with the Ollama inference service.

```bash
cd ../revela-app

gcloud run deploy revela-app \
  --source . \
  --region=europe-west4 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --port=8080 \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=120 \
  --set-env-vars=ENVIRONMENT=production,OLLAMA_HOST=$OLLAMA_URL,OLLAMA_MODEL=gemma3:12b-it-qat
```

**Detailed Parameter Breakdown:**

**Resource Allocation (CPU-optimized):**
- `--memory=2Gi`: 2 GiB RAM for Flask, session management, and data processing
- `--cpu=2`: 2 vCPUs for handling concurrent API requests
- No GPU needed—all AI inference happens in the Ollama service

**Scaling Configuration:**
- `--min-instances=0`: Scales to zero during idle periods
- `--max-instances=10`: Supports up to 800 concurrent connections (80 per instance default)

**Environment Variables:**
- `ENVIRONMENT=production`: Enables service-to-service authentication
- `OLLAMA_HOST=$OLLAMA_URL`: The Ollama service URL for LLM requests
- `OLLAMA_MODEL=gemma3:12b-it-qat`: Specifies which model to use

**Cost Comparison:**
- Backend: ~$0.053/hour per instance
- Ollama GPU: ~$0.60/hour per instance
- This architecture minimizes expensive GPU usage

### Step 4: Configure Service-to-Service Authentication

Grant the backend permission to invoke the Ollama service:

```bash
# Get the service account of revela-app
BACKEND_SA=$(gcloud run services describe revela-app \
  --region=europe-west4 \
  --format='value(spec.template.spec.serviceAccountName)')

# Grant invoker role to access Ollama service
gcloud run services add-iam-policy-binding ollama-gemma \
  --region=europe-west4 \
  --member="serviceAccount:$BACKEND_SA" \
  --role="roles/run.invoker"
```

This enables the Flask backend to authenticate with Ollama using Cloud Run's built-in IAM—no API keys needed!

### Step 5: Test the Deployment

```bash
BACKEND_URL=$(gcloud run services describe revela-app \
  --region=europe-west4 \
  --format='value(status.url)')

curl $BACKEND_URL/health
```

Expected response:
```json
{"status": "healthy", "model": "gemma3:12b-it-qat"}
```

Your services are now live! The Chrome extension can be configured to use `$BACKEND_URL` as its API endpoint.

## Understanding Cloud Run Service-to-Service Authentication

One of the most powerful features of this architecture is the secure communication between services. Let me break down exactly how this works.

### The Authentication Challenge

We have two Cloud Run services that need to communicate:
- **revela-app** (Flask backend) needs to call **ollama-gemma** (LLM service)
- The Ollama service should only accept requests from authorized sources
- We don't want to manage API keys or secrets

### The Solution: IAM-based Authentication

Cloud Run provides built-in service-to-service authentication using Google's Identity and Access Management (IAM). Here's the complete flow:

#### Step 1: IAM Configuration

When we run this command:

```bash
gcloud run services add-iam-policy-binding ollama-gemma \
  --region=europe-west4 \
  --member="serviceAccount:BACKEND_SERVICE_ACCOUNT" \
  --role="roles/run.invoker"
```

We're saying: "The backend service account is allowed to invoke the Ollama service."

#### Step 2: Token Generation (Backend Side)

When the Flask backend wants to call Ollama, it generates an ID token:

```python
# In config_module.py
import google.auth.transport.requests
import google.oauth2.id_token

auth_req = google.auth.transport.requests.Request()
id_token = google.oauth2.id_token.fetch_id_token(
    auth_req, 
    self.ollama_host  # e.g., "https://ollama-gemma-xyz.run.app"
)
headers["Authorization"] = f"Bearer {id_token}"
```

**What happens internally:**

1. **Metadata Server Query**: The code queries the GCP metadata server (available only inside Cloud Run)
2. **Service Account Identity**: The metadata server returns the service account credentials
3. **Token Request**: A JWT token is requested with:
   - **Issuer**: The backend service account
   - **Audience**: The Ollama service URL
   - **Expiration**: 1 hour from generation
4. **Token Signing**: Google signs the token with its private key
5. **Token Return**: The signed JWT is returned to the backend

#### Step 3: Making the Authenticated Request

The backend includes the token in the request:

```python
response = requests.post(
    "https://ollama-gemma-xyz.run.app/api/generate",
    json=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
)
```

#### Step 4: Token Validation (Cloud Run Infrastructure)

Before the request reaches the Ollama container, Cloud Run's infrastructure:

1. **Extracts the Token**: Parses the `Authorization` header
2. **Verifies Signature**: Validates the JWT signature using Google's public keys
3. **Checks Audience**: Ensures the token audience matches the Ollama service URL
4. **Validates Expiration**: Confirms the token hasn't expired
5. **Checks IAM Policy**: Verifies the service account has the `run.invoker` role
6. **Allows or Denies**: If all checks pass, the request is forwarded to the container

#### Step 5: Request Processing

The Ollama container receives the request as if it were a normal HTTP request—it doesn't need to handle authentication at all. Cloud Run has already verified the caller's identity.

### The Complete Flow Visualized

```
┌──────────────────────────────────────────────────────────────────┐
│                          FLASK BACKEND                           │
│                         (revela-app)                             │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               │ 1. Need to call Ollama
                               ▼
                    ┌──────────────────────┐
                    │  Metadata Server     │
                    │  (GCP Infrastructure)│
                    └──────────┬───────────┘
                               │
                               │ 2. Request ID token for
                               │    audience: ollama-gemma URL
                               ▼
                    ┌──────────────────────┐
                    │  Google Auth System  │
                    │  - Get service account
                    │  - Generate JWT
                    │  - Sign with private key
                    └──────────┬───────────┘
                               │
                               │ 3. Return signed token
                               │    eyJhbGciOiJSUzI1NiIs...
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                          FLASK BACKEND                           │
│  headers = {                                                     │
│    "Authorization": "Bearer eyJhbGciOiJSUzI1NiIs..."            │
│  }                                                               │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               │ 4. POST /api/generate
                               │    with Authorization header
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   CLOUD RUN INFRASTRUCTURE                       │
│  - Intercept request                                             │
│  - Extract Bearer token                                          │
│  - Verify JWT signature (Google's public keys)                   │
│  - Check audience matches ollama-gemma URL                       │
│  - Check expiration time                                         │
│  - Query IAM: Does service account have run.invoker?             │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               │ 5. ✓ All checks passed
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      OLLAMA CONTAINER                            │
│                      (ollama-gemma)                              │
│  - Receives authenticated request                                │
│  - No auth code needed in container                              │
│  - Processes inference                                           │
│  - Returns response                                              │
└──────────────────────────────────────────────────────────────────┘
```

### Key Benefits of This Approach

**1. Zero Secret Management**
- No API keys stored in code or environment variables
- No risk of keys being committed to git
- No need for secret rotation procedures

**2. Automatic Token Rotation**
- Tokens expire after 1 hour
- New tokens are generated automatically on each request
- No manual intervention required

**3. Fine-Grained Access Control**
- Each service has its own identity
- Permissions are managed through IAM roles
- Easy to audit who can call what

**4. Complete Audit Trail**
- All service-to-service calls are logged
- Can see which service account made each request
- Helps with compliance and debugging

**5. Defense in Depth**
- Even if Ollama URL is discovered, it can't be called without proper credentials
- Prevents unauthorized access from external sources
- Works seamlessly with Cloud Run's VPC features

### Local Development vs Production

The beauty of this implementation is it works in both environments:

**Local Development:**
```python
if self.environment == "local":
    # No authentication needed
    headers = {"Content-Type": "application/json"}
```

**Production (Cloud Run):**
```python
if self.environment == "production":
    # Automatic service-to-service auth
    id_token = google.oauth2.id_token.fetch_id_token(auth_req, target_url)
    headers["Authorization"] = f"Bearer {id_token}"
```

The same code works everywhere, with authentication enabled automatically in production.

## Essential Cloud Run Management Commands

Once deployed, use these commands to manage your services:

### Viewing Logs

```bash
# Stream logs in real-time
gcloud run services logs read revela-app \
  --region=europe-west4 \
  --follow
```

### Updating Services

```bash
# Update environment variables
gcloud run services update revela-app \
  --region=europe-west4 \
  --update-env-vars=OLLAMA_MODEL=gemma3:12b-it-qat

# Update scaling
gcloud run services update ollama-gemma \
  --region=europe-west4 \
  --min-instances=1 \
  --max-instances=10
```

### Traffic Management

```bash
# Split traffic between revisions
gcloud run services update-traffic revela-app \
  --region=europe-west4 \
  --to-revisions=revela-app-00003-abc=50,revela-app-00004-def=50
```

Cloud Run creates a new revision for each deployment, enabling easy rollbacks and gradual rollouts.

## Performance and Cost Optimization

### Cold Start Management
- Set `--min-instances=0` for cost savings (scales to zero when idle)
- Use `OLLAMA_KEEP_ALIVE=30m` to keep the model warm between requests
- First request after idle: ~30-60 seconds (model loading)
- Subsequent requests: <2 seconds

### Resource Right-sizing
Through monitoring, I optimized resource allocation:
- **Backend**: 2 vCPU, 2 GiB RAM → handles 100+ concurrent sessions
- **Ollama**: 4 vCPU, 8 GiB RAM, 1 GPU → handles 10-15 concurrent inferences

### Streaming Responses
All LLM responses stream in real-time for better UX, reducing perceived latency.

## Cost Analysis

**Backend API Service:**
- CPU: ~$0.024 per vCPU hour
- Memory: ~$0.0025 per GiB hour
- Request: ~$0.40 per million requests

**Ollama GPU Service:**
- GPU (L4): ~$0.48 per hour
- CPU/Memory: Standard Cloud Run pricing

**Example monthly cost** (moderate usage):
- 1000 analysis sessions
- Average 2 minutes per session
- Backend: ~$5/month
- Ollama GPU: ~$16/month
- Total: ~$21/month

With auto-scaling to zero, idle periods cost nothing.

## Key Learnings

### 1. GPU Support is Game-Changing

Cloud Run's GPU support made it possible to run a 12B parameter model efficiently. Without this, I would have needed to use smaller, less capable models or incur significant costs with always-on GPU instances.

### 2. Source-based Deployment Simplifies CI/CD

Being able to deploy with `gcloud run deploy --source .` eliminated the need to manage Docker registries and image tags. This significantly accelerated development iterations.

### 3. Service-to-Service Auth is Seamless

Cloud Run's built-in IAM made it trivial to secure communication between services. No need to manage API keys or custom authentication logic.

### 4. Auto-scaling Requires Careful Planning

While auto-scaling is powerful, I had to carefully consider:
- Model loading time on cold starts
- Session state management across instances
- Timeout configurations for long-running requests

### 5. Privacy-First Design Matters

Implementing ephemeral sessions with automatic cleanup ensured user privacy while simplifying data management. No database required!

## Future Enhancements

1. **Multi-modal Analysis**: Support for PDFs and other document types
2. **Collaborative Sessions**: Share analysis sessions with team members
3. **Export Capabilities**: Export insights as reports or presentations
4. **Custom Model Fine-tuning**: Domain-specific models for specialized analysis
5. **Real-time Collaboration**: Multiple users analyzing the same data simultaneously

## Conclusion

Building Revela with Google Cloud Run was an incredibly rewarding experience. The platform's serverless architecture, GPU support, and developer-friendly features enabled me to focus on building innovative features rather than managing infrastructure.

Cloud Run's auto-scaling, pay-per-use pricing, and source-based deployments made it the ideal platform for a hackathon project that needed to be both production-ready and cost-effective.

Whether you're building AI applications, web services, or data processing pipelines, Cloud Run provides the flexibility and power to bring your ideas to life quickly and efficiently.

## Resources

- **Project Repository**: [GitHub - Revela](https://github.com/mmohanram13/revela)
- **Live Demo**: [Try Revela](https://revela-app-759597171569.europe-west4.run.app)
- **Google Cloud Run Documentation**: [cloud.google.com/run](https://cloud.google.com/run)
- **Gemma Model**: [ai.google.dev/gemma](https://ai.google.dev/gemma)
- **Ollama**: [ollama.com](https://ollama.com)

---

**About the Author**: I'm a developer passionate about making AI accessible and practical for everyday use. This project was created for the Google Cloud Run Hackathon to explore the possibilities of serverless AI applications.

**Hashtags**: #GoogleCloudRun #Hackathon #AI #MachineLearning #Gemma #ChromeExtension #Serverless #GPU #DataAnalysis
