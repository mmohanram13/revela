# Revela System Architecture

## Overview

Revela implements a **stateless, ephemeral architecture** optimized for Google Cloud Run, providing privacy-first AI analysis of web-based data visualizations.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         Browser Layer                             │
│  ┌────────────────────────────────────────────────────────┐      │
│  │              Chrome Extension (Frontend)                │      │
│  │                                                          │      │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────┐       │      │
│  │  │  Content │  │Background│  │  Popup UI      │       │      │
│  │  │  Script  │──│ Worker   │──│                │       │      │
│  │  └──────────┘  └──────────┘  └────────────────┘       │      │
│  │                                                          │      │
│  │  Features:                                              │      │
│  │  • Detects tables & chart images                       │      │
│  │  • Hover icon (logo.png) on analyzable elements        │      │
│  │  • Quick Insights / Deep Analyse actions               │      │
│  │  • Sidebar chat interface                              │      │
│  │  • Session ID generation                               │      │
│  └────────────┬───────────────────────────────────────────┘      │
└───────────────┼──────────────────────────────────────────────────┘
                │
                │ HTTPS (JSON Payload)
                │ - sessionId
                │ - data (HTML/image)
                │ - url
                ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Application Layer                            │
│          Google Cloud Run - CPU Instance                         │
│  ┌────────────────────────────────────────────────────────┐      │
│  │           Backend API Service (Flask)                  │      │
│  │                                                          │      │
│  │  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │      │
│  │  │  Session     │  │   DuckDB    │  │  Ollama      │  │      │
│  │  │  Manager     │──│  In-Memory  │  │  Client      │  │      │
│  │  └──────────────┘  └─────────────┘  └──────┬───────┘  │      │
│  │                                             │           │      │
│  │  API Endpoints:                             │           │      │
│  │  • POST /api/session/start                 │           │      │
│  │  • POST /api/quick-insights                │           │      │
│  │  • POST /api/deep-analyse                  │           │      │
│  │  • POST /api/session/end                   │           │      │
│  │  • GET  /health                             │           │      │
│  │                                             │           │      │
│  │  Session Features:                          │           │      │
│  │  • Ephemeral (30 min timeout)              │           │      │
│  │  • In-memory DuckDB per session            │           │      │
│  │  • HTML table parsing                      │           │      │
│  │  • SQL-based analytics                     │           │      │
│  │  • Conversation history                    │           │      │
│  │  • Auto cleanup                             │           │      │
│  └─────────────────────────────────────────────┼──────────┘      │
│                                                 │                 │
│  Resources:                                     │                 │
│  • 2 vCPU, 2 GiB RAM                           │                 │
│  • Autoscale: 0 → 10 instances                 │                 │
│  • Concurrency: 80 requests/instance           │                 │
└─────────────────────────────────────────────────┼─────────────────┘
                                                  │
                                                  │ Internal HTTPS
                                                  │ (Service Auth)
                                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Model Layer                                │
│          Google Cloud Run - GPU Instance                         │
│  ┌────────────────────────────────────────────────────────┐      │
│  │        Inference Service (Ollama + Gemma)              │      │
│  │                                                          │      │
│  │  ┌──────────────┐                                       │      │
│  │  │   Ollama     │                                       │      │
│  │  │   Server     │                                       │      │
│  │  └──────┬───────┘                                       │      │
│  │         │                                                │      │
│  │         ▼                                                │      │
│  │  ┌──────────────┐                                       │      │
│  │  │  Gemma:12b    │                                       │      │
│  │  │  Model       │                                       │      │
│  │  └──────────────┘                                       │      │
│  │                                                          │      │
│  │  Capabilities:                                          │      │
│  │  • Natural language understanding                      │      │
│  │  • Data insight generation                             │      │
│  │  • Conversational responses                            │      │
│  │  • GPU-accelerated inference                           │      │
│  │                                                          │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                    │
│  Resources:                                                        │
│  • 4 vCPU, 8 GiB RAM                                              │
│  • 1x NVIDIA L4 GPU                                               │
│  • Autoscale: 0 → 5 instances                                     │
│  • Concurrency: 4 requests/instance                               │
└────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Quick Insights Flow

```
User hovers over table
         ↓
Hover icon appears (logo.png)
         ↓
User clicks "Quick Insights"
         ↓
Extension extracts element data
         ↓
Generate session ID
         ↓
POST /api/quick-insights
  {
    sessionId: "uuid",
    data: {type: "table", html: "..."},
    url: "https://..."
  }
         ↓
Backend creates temp session
         ↓
Parse HTML → DuckDB
         ↓
Generate summary stats
         ↓
Build LLM prompt with context
         ↓
Call Inference Service
         ↓
Receive AI insights
         ↓
Cleanup temp session
         ↓
Return JSON response
         ↓
Display tooltip with insights
```

### 2. Deep Analyse Flow

```
User clicks "Deep Analyse"
         ↓
POST /api/session/start
         ↓
Backend creates persistent session
  - sessionId: from extension
  - DuckDB instance in memory
  - Parse & store data
         ↓
Return session summary
         ↓
Extension opens sidebar
         ↓
User types question
         ↓
POST /api/deep-analyse
  {
    sessionId: "uuid",
    message: "What's the average?"
  }
         ↓
Backend retrieves session
         ↓
Build context from:
  - Data summary
  - Conversation history (last 5)
  - Current question
         ↓
Call Inference Service
         ↓
Receive AI response
         ↓
Store in conversation history
         ↓
Return response
         ↓
Display in chat sidebar
         ↓
(Repeat for more questions)
         ↓
User closes sidebar OR 30 min timeout
         ↓
POST /api/session/end (or auto-cleanup)
         ↓
Session destroyed
DuckDB connection closed
Memory freed
```

## Component Details

### Chrome Extension

**Responsibilities:**
- Element detection (tables, images)
- Hover UI management
- Data extraction (HTML, URLs)
- Session lifecycle coordination
- Sidebar chat interface

**Key Files:**
- `content.js`: Detection logic, UI creation, API calls
- `content.css`: Styled components (hover icon, tooltip, sidebar)
- `manifest.json`: Extension configuration

**Technology:**
- Vanilla JavaScript (ES6+)
- Chrome Extension Manifest V3
- CSS3 for animations

### Backend API (Cloud Run - CPU)

**Responsibilities:**
- RESTful API endpoints
- Session management with unique IDs
- DuckDB instance per session
- HTML table parsing
- SQL query generation
- LLM orchestration
- Auto-cleanup of expired sessions

**Key Files:**
- `app.py`: Flask routes, CORS, endpoints
- `session_manager.py`: Session lifecycle, DuckDB integration
- `ollama_client.py`: LLM communication
- `config_module.py`: Environment configuration

**Technology:**
- Python 3.11+
- Flask + Flask-CORS
- DuckDB (in-memory)
- Gunicorn (WSGI server)

**Session Management:**
- Thread-safe with locks
- Automatic cleanup every 5 minutes
- 30-minute timeout per session
- In-memory storage (no persistence)

### Inference Service (Cloud Run - GPU)

**Responsibilities:**
- Gemma model hosting
- Natural language processing
- Insight generation
- GPU-accelerated inference

**Key Files:**
- `Dockerfile`: Ollama + Gemma setup

**Technology:**
- Ollama server
- Google Gemma 7B model
- NVIDIA CUDA (L4 GPU)

**Performance:**
- Cold start: ~60-120s (GPU initialization)
- Warm inference: ~2-5s per query
- Concurrent requests: 4 per instance

## Security Architecture

### Network Security

```
Internet
   ↓
   ↓ HTTPS (TLS 1.3)
   ↓
Backend API (Public)
   ↓
   ↓ Internal HTTPS + IAM Auth
   ↓
Inference Service (Private)
```

**Security Layers:**
1. **Extension → Backend**: CORS-protected, HTTPS only
2. **Backend → Inference**: Service account authentication
3. **No Public Access**: Inference service private
4. **Ephemeral Data**: No persistent storage

### Data Privacy

- ✅ **Zero Persistence**: All data in-memory only
- ✅ **Session Isolation**: Unique DuckDB per session
- ✅ **Auto-Expiry**: 30-minute timeout
- ✅ **No Logging**: User data not logged
- ✅ **No Tracking**: No analytics on user content

## Scalability

### Auto-Scaling Behavior

**Backend (CPU):**
- Scales to 0 when idle
- Cold start: ~2-3 seconds
- Scales up to 10 instances under load
- Each instance handles 80 concurrent sessions

**Inference (GPU):**
- Scales to 0 when idle (optional: min=1 for lower latency)
- Cold start: ~60-120 seconds (GPU + model load)
- Scales up to 5 instances (GPU quota dependent)
- Each instance handles 4 concurrent requests

### Cost Optimization

- **Scale to Zero**: No cost when idle
- **Session Timeout**: Frees resources automatically
- **Ephemeral DuckDB**: No storage costs
- **GPU Selection**: L4 GPUs cost-effective for Gemma

## Monitoring & Observability

### Metrics

**Backend:**
- Active sessions count
- Session creation rate
- Average session duration
- DuckDB query latency
- API response times

**Inference:**
- Model inference latency
- GPU utilization
- Request queue depth
- Token throughput

### Logging

**Structured Logs:**
```json
{
  "severity": "INFO",
  "timestamp": "2025-11-10T...",
  "message": "Started session abc-123 for table",
  "sessionId": "abc-123",
  "dataType": "table",
  "service": "revela-backend"
}
```

**Cloud Logging Integration:**
- All logs shipped to Cloud Logging
- Searchable by session ID
- Retention: 30 days default

## Disaster Recovery

### Stateless Design Benefits

- ✅ **No Data Loss**: All data ephemeral by design
- ✅ **Instant Recovery**: New instances spin up automatically
- ✅ **No Backups Needed**: Nothing to restore
- ✅ **Geographic Redundancy**: Cloud Run multi-zone by default

### Failure Scenarios

| Scenario | Impact | Recovery |
|----------|--------|----------|
| Backend instance crash | Active sessions lost | User retries, new session |
| Inference timeout | Request fails | Automatic retry with exponential backoff |
| DuckDB memory limit | Session creation fails | Return error, user reduces data size |
| GPU quota exhausted | Inference queued | Auto-scales when quota available |

## Future Enhancements

### Potential Improvements

1. **Streaming Responses**: Server-Sent Events for real-time insights
2. **Multi-Table Analysis**: Join across multiple tables on page
3. **Advanced Visualizations**: Generate charts from table data
4. **Export Features**: PDF/CSV export of insights
5. **Custom Models**: User-selectable LLM variants
6. **Caching Layer**: Redis for common query patterns
7. **Batch Processing**: Analyze multiple tables at once

### Scaling Considerations

- **Regional Deployment**: Multi-region for global latency
- **CDN Integration**: Cache static assets
- **Database Upgrade**: PostgreSQL for persistent sessions (if needed)
- **Message Queue**: Pub/Sub for async processing

---

**This architecture prioritizes privacy, scalability, and cost-efficiency while maintaining simplicity and cloud-native best practices.**
