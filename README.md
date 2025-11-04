# Revela

> Right-click any chart or table on the web to get instant AI insights, powered by Gemma on Cloud Run

Revela is a Chrome extension with a Streamlit web application that provides AI-powered analysis of charts and tables using Ollama and Google's Gemma models.

## 🚀 Quick Start

### Streamlit App

```bash
# Quick start (recommended)
./start-app.sh

# Or manually
source .venv/bin/activate
uv run streamlit run application/app.py
```

Access the app at: http://localhost:8501

### Chrome Extension

1. Install dependencies:
   ```bash
   cd chrome-extension
   npm install
   ```

2. Load in Chrome:
   - Open `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `chrome-extension` directory

3. Usage:
   - Right-click on any chart/table image
   - Select "Analyze with Revela"

## 📁 Project Structure

```
revela/
├── application/           # Streamlit web application
│   ├── app.py            # Main Streamlit app
│   ├── config.py         # Configuration management
│   ├── ollama_client.py  # Ollama API client with auth
│   ├── .env.example      # Environment template
│   └── images/           # App assets
├── chrome-extension/      # Chrome extension
│   ├── manifest.json     # Extension manifest
│   ├── background.js     # Background service worker
│   ├── content.js        # Content script
│   ├── popup.html/js/css # Extension UI
│   ├── package.json      # npm dependencies
│   └── images/           # Extension icons
├── ollama-gemma/         # Ollama + Gemma Docker setup
│   ├── Dockerfile        # Ollama container
│   └── README.md         # Ollama setup guide
├── Dockerfile            # Cloud Run deployment
├── pyproject.toml        # Python dependencies
└── start-app.sh          # Quick start script
```

## ✨ Features

### Streamlit Web App
- 🔍 **Extension Detection**: Alerts if Chrome extension is not installed
- 💬 **Text Prompts**: Ask questions about charts and tables
- 🖼️ **Image Support**: Upload or paste images for analysis
- 🤖 **AI Analysis**: Powered by Ollama with Gemma models
- ☁️ **Cloud Ready**: Deploy to Google Cloud Run with OIDC auth
- 📊 **Real-time Streaming**: Live response streaming from AI

### Chrome Extension
- 🖱️ **Right-click Context Menu**: Analyze any image on the web
- 📊 **Chart & Table Detection**: Automatic visualization detection
- 🎨 **Clean Popup UI**: Minimal, user-friendly interface
- 🔗 **Backend Integration**: Seamlessly connects to Streamlit app
- ⚡ **Fast & Lightweight**: Minimal resource usage

## 🛠️ Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Ollama (local or Cloud Run)
- Node.js & npm (for Chrome extension)

### Python Environment Setup

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv add streamlit python-dotenv pillow google-auth requests ollama watchdog
```

### Configuration

1. **Copy environment template:**
   ```bash
   cp application/.env.example application/.env
   ```

2. **Edit `application/.env`:**
   ```env
   ENVIRONMENT=local
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=gemma3:12b-it-qat
   ```

3. **Start Ollama:**
   ```bash
   # Using Docker (recommended)
   cd ollama-gemma
   docker build -t ollama-gemma .
   docker run -p 11434:11434 ollama-gemma
   
   # Or use local Ollama
   ollama serve
   ```

### Running Locally

```bash
# Start the Streamlit app
./start-app.sh

# Or manually
uv run streamlit run application/app.py
```

## ☁️ Cloud Deployment

### Prerequisites

- Google Cloud Project with billing enabled
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- Ollama backend deployed on Cloud Run (see [ollama-gemma/README.md](ollama-gemma/README.md))

### Deploy Streamlit App to Cloud Run

```bash
# Deploy from project root (where Dockerfile is located)
gcloud run deploy revela-app \
  --source . \
  --region europe-west4 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production,OLLAMA_HOST=https://your-ollama-service.run.app,OLLAMA_MODEL=gemma3:12b-it-qat \
  --cpu 2 \
  --memory 2Gi \
  --timeout 300 \
  --max-instances 1 \
  --min-instances 0
```

Replace `https://your-ollama-service.run.app` with your actual Ollama service URL.

**Important**: Run this command from the **project root directory** where `Dockerfile` and `pyproject.toml` are located.

### Service-to-Service Authentication

If your Ollama backend requires authentication:

```bash
# Get the service account email
SERVICE_ACCOUNT=$(gcloud run services describe revela-app \
  --region europe-west4 \
  --format 'value(spec.template.spec.serviceAccountName)')

# Grant invoker role to access Ollama service
gcloud run services add-iam-policy-binding ollama-gemma \
  --region europe-west4 \
  --member "serviceAccount:$SERVICE_ACCOUNT" \
  --role "roles/run.invoker"
```

### Environment Variables

Production environment variables in Cloud Run:

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `production` |
| `OLLAMA_HOST` | Ollama backend URL | `https://ollama.run.app` |
| `OLLAMA_MODEL` | Model to use | `gemma3:12b-it-qat` |
| `STREAMLIT_SERVER_PORT` | Server port (auto-set) | `8080` |

## 🔐 Authentication & Security

The application automatically handles authentication based on environment:

- **Local** (`ENVIRONMENT=local`): No authentication required
- **Production** (`ENVIRONMENT=production`): Google Cloud OIDC tokens for service-to-service auth

### Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Browser   │─────▶│  Streamlit   │─────▶│   Ollama    │
│             │      │     App      │      │   Backend   │
│  (User)     │◀─────│ (Cloud Run)  │◀─────│ (Cloud Run) │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ OIDC Token   │
                     │ Generation   │
                     └──────────────┘
```

- Credentials managed through Google Cloud IAM
- No API keys in environment variables
- Secure service-to-service communication

## 📖 Additional Documentation

- [Ollama + Gemma Setup](ollama-gemma/README.md) - Docker setup for Ollama backend

## 🧪 Usage

1. **Start the app** with `./start-app.sh`
2. **Check extension status** - the app will alert if not installed
3. **Enter your question** about a chart or table
4. **Upload an image** (optional) of the chart/table
5. **Click Analyze** to get AI-powered insights
6. **View results** streaming in real-time

## 🤝 Contributing

This project follows Python best practices:
- Use `uv` for package management (not `pip`)
- Use `npm` for Chrome extension dependencies
- Always run in virtual environment
- Keep dependencies in `pyproject.toml`

## 📝 Common Commands

| Task | Command |
|------|---------|
| Create venv | `uv venv` |
| Activate venv | `source .venv/bin/activate` |
| Install packages | `uv add <package>` |
| Run app | `uv run streamlit run application/app.py` |
| Quick start | `./start-app.sh` |

## 🐛 Troubleshooting

### Streamlit App Issues

#### Cannot connect to Ollama service
- **Local**: Ensure Ollama is running on `http://localhost:11434`
  ```bash
  curl http://localhost:11434/api/tags
  ```
- **Production**: Verify `OLLAMA_HOST` is correct and service is deployed
- Check `.env` configuration matches your setup

#### Import errors during local development
```bash
# Ensure you're in the virtual environment
source .venv/bin/activate

# Reinstall dependencies
uv add streamlit python-dotenv pillow google-auth requests ollama watchdog
```

#### Authentication errors in production
- Verify service account has `roles/run.invoker` permission
- Check Cloud Run logs:
  ```bash
  gcloud run logs read --service revela-app --region europe-west4
  ```

### Chrome Extension Issues

#### Extension not detected by app
- The app shows an alert - click "I have installed the extension" to dismiss
- Verify extension is loaded in `chrome://extensions/`
- Ensure extension is enabled

#### Extension not working
1. Go to `chrome://extensions/`
2. Find Revela and click the refresh icon
3. Check the browser console for errors (F12)

#### Cannot connect to backend
- Verify the Streamlit app is running at `http://localhost:8501`
- Check extension settings for correct API endpoint
- Ensure CORS is properly configured

### Development Issues

#### Virtual environment not activating
```bash
# Recreate the environment
uv venv
source .venv/bin/activate
```

#### Dependencies not installing
```bash
# Update uv
pip install --upgrade uv

# Clear cache and reinstall
uv pip install --system --no-cache .
```

## 📄 License

Part of the Revela project for AI-powered web content analysis.

---

**Built with** ❤️ using Streamlit, Ollama, and Google Gemma
