# Revela

> AI-powered insights for tables and charts on any webpage — instant analysis with hover icons and deep conversational exploration

Revela is a Chrome extension with a Cloud Run backend that provides ephemeral, privacy-first AI analysis of data visualizations using Google's Gemma models.

## 🏗️ System Architecture

Revela uses a **stateless, ephemeral architecture** designed for Cloud Run:

### Core Components

1. **Chrome Extension (Frontend)**
   - Detects tables and chart images on web pages
   - Shows hover icons (using logo.png only) beside analyzable elements
   - Offers two interaction modes:
     - **Quick Insights**: Instant summary of data
     - **Deep Analyse**: Interactive sidebar chat

2. **Backend API (Cloud Run - CPU)**
   - Manages ephemeral analysis sessions
   - In-memory DuckDB for table processing
   - Orchestrates LLM queries
   - Auto-cleanup after 30 min inactivity

3. **Ollama Service** (Optional separate deployment)
   - Ollama + Gemma model inference
   - Can be GPU-accelerated or use local instance
   - Stateless request handling

### Key Advantages

✅ **Privacy-First**: No persistent storage of user data  
✅ **Auto-Scaling**: Scales to zero when idle  
✅ **Cloud Native**: Built for Google Cloud Run  
✅ **Simple Deployment**: Source-based deployment, no build configs needed  
✅ **Ephemeral Sessions**: Clean state for every analysis

## 🚀 Quick Start

### Local Development

#### 1. Backend (Flask + DuckDB)

```bash
cd revela-app

# Ensure virtual environment exists
uv venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if needed)
uv sync

# Start the backend
./start-app.sh
```

Access at: http://localhost:8080

#### 2. Ollama (Inference Service)

```bash
# Run Ollama locally
ollama serve
ollama pull gemma:7b

# Or use Docker
cd ollama-gemma
docker build -t revela-ollama .
docker run -p 11434:11434 revela-ollama
```

#### 3. Chrome Extension

```bash
cd chrome-extension

# Install dependencies
npm install

# Build extension (if needed)
npm run build
```

Load in Chrome:
1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `chrome-extension/dist` directory (or `chrome-extension` if no build step)

### Cloud Deployment

See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for complete Cloud Run deployment instructions.

Quick deploy:

```bash
# Set your GCP project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Deploy from revela-app directory
cd revela-app
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
  --set-env-vars OLLAMA_HOST=https://your-ollama-service.run.app
```

## 📁 Project Structure

```
revela/
├── chrome-extension/          # Chrome extension
│   ├── public/
│   │   ├── manifest.json     # Extension manifest (uses logo.png only)
│   │   └── images/
│   │       └── logo.png      # Single icon for all uses
│   └── src/
│       ├── background/        # Background service worker
│       ├── content/           # Content scripts (hover detection)
│       │   ├── content.js    # Main detection and UI logic
│       │   └── content.css   # Styled hover icons, sidebar, tooltips
│       └── popup/             # Extension popup UI
│
├── revela-app/                # Backend API (Cloud Run CPU)
│   ├── src/
│   │   ├── app.py            # Flask routes and API endpoints
│   │   ├── session_manager.py # Ephemeral session management
│   │   ├── ollama_client.py  # LLM client
│   │   └── config_module.py  # Configuration
│   ├── ui/                    # Web interface assets
│   ├── Dockerfile            # Cloud Run Dockerfile
│   ├── pyproject.toml        # Python dependencies (uv)
│   └── start-app.sh          # Local startup script
│
├── ollama-gemma/              # Ollama service (optional)
│   ├── Dockerfile            # Ollama + Gemma container
│   └── README.md
│
├── DEPLOYMENT.md              # Deployment guide
├── ARCHITECTURE.md            # System architecture
└── README.md                  # This file
```

## ✨ Features

### Chrome Extension

- 🎯 **Automatic Detection**: Recognizes tables and chart images on any webpage
- 🖼️ **Single Icon**: Uses logo.png only (no icon clutter)
- ⚡ **Quick Insights**: Hover icon → Click → Instant summary tooltip
- 💬 **Deep Analyse**: Opens interactive sidebar for conversational exploration
- 🔒 **Privacy-First**: No tracking, no persistent storage
- 🌐 **Works Everywhere**: Analyzes data on any website

### Backend API

- 📊 **DuckDB Integration**: In-memory SQL analytics for tables
- 🔄 **Ephemeral Sessions**: Unique session IDs, auto-expire after 30 min
- 🧠 **LLM-Powered**: Gemma model for insights generation
- 🌊 **RESTful API**: Clean endpoints for extension communication
- 📈 **Summary Statistics**: Automatic table profiling

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/session/start` | POST | Start new analysis session |
| `/api/quick-insights` | POST | Get instant insights (no session) |
| `/api/deep-analyse` | POST | Conversational analysis |
| `/api/session/end` | POST | End session, cleanup resources |
| `/health` | GET | Health check + active sessions |

## 🛠️ Development

### Prerequisites

- **Python**: 3.11+
- **Package Manager**: [uv](https://github.com/astral-sh/uv)
- **Node.js**: 18+ (for extension)
- **Ollama**: Local or Cloud Run
- **Docker**: For containerization (optional)

### Backend Development

```bash
cd revela-app

# Install new package
uv add <package-name>

# Run locally
./start-app.sh

# Run with gunicorn manually
uv run gunicorn --bind 0.0.0.0:8080 --workers 2 --reload src.app:app
```

### Extension Development

```bash
cd chrome-extension

# Install package
npm install <package-name>

# Development mode
npm run dev
```

### Testing Session Management

```bash
# Start backend
cd revela-app && ./start-app.sh

# Test session creation
curl -X POST http://localhost:8080/api/session/start \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-123",
    "data": {
      "type": "table",
      "html": "<table><tr><th>Name</th></tr><tr><td>Test</td></tr></table>"
    },
    "url": "http://example.com"
  }'

# Test quick insights
curl -X POST http://localhost:8080/api/quick-insights \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "quick-456",
    "data": {
      "type": "table",
      "html": "<table><tr><th>Col1</th><th>Col2</th></tr><tr><td>A</td><td>1</td></tr></table>"
    },
    "url": "http://example.com"
  }'
```

## 🔧 Configuration

### Backend Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Runtime environment | `development` |
| `OLLAMA_HOST` | Ollama service URL | `http://localhost:11434` |
| `PORT` | Server port | `8080` |

### Extension Configuration

Update `content.js`:

```javascript
// For local development
const API_ENDPOINT = 'http://localhost:8080';

// For production
const API_ENDPOINT = 'https://your-backend.run.app';
```

## 📊 Session Lifecycle

1. **Hover Detection** → User hovers over table/chart
2. **Icon Display** → Hover icon (logo.png) appears
3. **User Action** → Clicks "Quick Insights" or "Deep Analyse"
4. **Session Creation** → Unique session ID generated
5. **Data Extraction** → HTML table or image data sent to backend
6. **DuckDB Processing** → Table parsed into in-memory database
7. **LLM Query** → Context sent to Gemma for insights
8. **Response Display** → Tooltip or sidebar shows results
9. **Auto-Cleanup** → Session expires after 30 min or manual close

## 🌐 Deployment

### Cloud Run Architecture

```
┌─────────────────┐
│ Chrome Extension│
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  Backend API    │ (Cloud Run - CPU)
│  - Sessions     │ - 2 vCPU, 2GB RAM
│  - DuckDB       │ - Source deploy
│  - Orchestration│ - Autoscale 0→N
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│ Ollama Service  │ (Local or Cloud Run)
│  - Gemma Model  │ - Optional GPU
│  - Inference    │
└─────────────────┘
```

**See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions**

### Simple Source Deployment

No build configs needed! Cloud Run builds from source:

```bash
cd revela-app
gcloud run deploy revela-app --source .
```

## 🔒 Security & Privacy

- ✅ **No Persistent Storage**: All data ephemeral
- ✅ **HTTPS Only**: Encrypted communication
- ✅ **Service-to-Service Auth**: IAM-based internal calls (optional)
- ✅ **CORS Protection**: Restricted origins
- ✅ **Auto-Cleanup**: Sessions destroyed after timeout
- ✅ **No Tracking**: Zero analytics or user monitoring

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Support for more chart types (SVG, Canvas)
- [ ] Advanced SQL query generation
- [ ] Multi-table relationship analysis
- [ ] Export insights to CSV/PDF
- [ ] Custom model selection

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **Google Gemma**: State-of-the-art language model
- **Ollama**: Simplified LLM deployment
- **DuckDB**: Fast in-memory analytics
- **Cloud Run**: Serverless container platform

---

**Built with ❤️ for data enthusiasts**
