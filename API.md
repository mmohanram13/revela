# Revela API Reference

## Base URL

**Local Development:**
```
http://localhost:8080
```

**Production (Cloud Run):**
```
https://revela-backend-[hash]-uc.a.run.app
```

---

## Authentication

Currently no authentication required for local development.

For Cloud Run production:
- Extension → Backend: CORS-protected, allow-unauthenticated
- Backend → Inference: IAM service account authentication

---

## Endpoints

### 1. Health Check

**GET** `/health`

Check the health status of the backend service.

**Request:**
```bash
curl http://localhost:8080/health
```

**Response:**
```json
{
  "status": "healthy",
  "ollama": true,
  "environment": "development",
  "active_sessions": 3
}
```

**Status Codes:**
- `200 OK`: Service is healthy

---

### 2. Start Session

**POST** `/api/session/start`

Initialize a new analysis session with data from a web page.

**Request:**
```bash
curl -X POST http://localhost:8080/api/session/start \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "550e8400-e29b-41d4-a716-446655440000",
    "data": {
      "type": "table",
      "html": "<table><tr><th>Name</th><th>Age</th></tr><tr><td>Alice</td><td>30</td></tr></table>",
      "rowCount": 2,
      "colCount": 2
    },
    "url": "https://example.com/data"
  }'
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sessionId` | string | Yes | Unique UUID for the session |
| `data` | object | Yes | Element data to analyze |
| `data.type` | string | Yes | `table`, `image`, or `canvas` |
| `data.html` | string | For tables | Full HTML of the table |
| `data.src` | string | For images | Image source URL |
| `data.dataUrl` | string | For canvas | Base64 data URL |
| `url` | string | Yes | Source page URL |

**Response:**
```json
{
  "success": true,
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "summary": {
    "type": "table",
    "row_count": 1,
    "column_count": 2,
    "columns": ["name", "age"],
    "sample_rows": [
      ["Alice", "30"]
    ]
  }
}
```

**Status Codes:**
- `200 OK`: Session created successfully
- `400 Bad Request`: Missing required fields
- `500 Internal Server Error`: Session creation failed

---

### 3. Quick Insights

**POST** `/api/quick-insights`

Generate instant insights without creating a persistent session.

**Request:**
```bash
curl -X POST http://localhost:8080/api/quick-insights \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "temp-123",
    "data": {
      "type": "table",
      "html": "<table><tr><th>Product</th><th>Sales</th></tr><tr><td>Widget</td><td>1000</td></tr><tr><td>Gadget</td><td>1500</td></tr></table>"
    },
    "url": "https://example.com/sales"
  }'
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sessionId` | string | Yes | Temporary session ID |
| `data` | object | Yes | Element data to analyze |
| `url` | string | Yes | Source page URL |

**Response:**
```json
{
  "success": true,
  "insights": "Based on the sales data:\n\n1. Total Revenue: The combined sales show $2,500 in revenue\n2. Top Performer: Gadget leads with 1,500 units (60% of total)\n3. Product Mix: Two products in the catalog\n4. Average Sales: 1,250 units per product\n5. Growth Opportunity: Widget underperforms relative to Gadget",
  "summary": {
    "type": "table",
    "row_count": 2,
    "column_count": 2,
    "columns": ["product", "sales"]
  }
}
```

**Status Codes:**
- `200 OK`: Insights generated successfully
- `400 Bad Request`: Invalid data or missing fields
- `500 Internal Server Error`: Analysis failed

---

### 4. Deep Analyse

**POST** `/api/deep-analyse`

Conversational analysis for an active session.

**Request:**
```bash
curl -X POST http://localhost:8080/api/deep-analyse \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "550e8400-e29b-41d4-a716-446655440000",
    "message": "What is the average age?"
  }'
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sessionId` | string | Yes | Active session ID |
| `message` | string | Yes | User's question or request |

**Response:**
```json
{
  "success": true,
  "response": "Based on the data in this table, the average age is 30. There is only one entry (Alice, age 30), so that value represents both the only data point and the average."
}
```

**Status Codes:**
- `200 OK`: Response generated successfully
- `400 Bad Request`: Missing sessionId or message
- `404 Not Found`: Session not found or expired
- `500 Internal Server Error`: Analysis failed

---

### 5. End Session

**POST** `/api/session/end`

Manually end an analysis session and free resources.

**Request:**
```bash
curl -X POST http://localhost:8080/api/session/end \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sessionId` | string | Yes | Session ID to terminate |

**Response:**
```json
{
  "success": true,
  "message": "Session ended"
}
```

**Status Codes:**
- `200 OK`: Session ended successfully
- `400 Bad Request`: Missing sessionId
- `500 Internal Server Error`: Cleanup failed

---

## Data Types

### Table Data
```json
{
  "type": "table",
  "html": "<table>...</table>",
  "rowCount": 10,
  "colCount": 5
}
```

### Image Data
```json
{
  "type": "image",
  "src": "https://example.com/chart.png",
  "alt": "Sales Chart",
  "width": 800,
  "height": 600
}
```

### Canvas Data
```json
{
  "type": "canvas",
  "dataUrl": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "width": 1024,
  "height": 768
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Description of what went wrong"
}
```

### Common Errors

**400 Bad Request:**
```json
{
  "error": "Missing required fields"
}
```

**404 Not Found:**
```json
{
  "error": "Session not found or expired"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Error creating session: DuckDB initialization failed"
}
```

---

## CORS

The backend is configured to accept requests from:
- Chrome extension origins: `chrome-extension://*`
- Local development: `http://localhost:*`

**Allowed Methods:**
- GET
- POST
- OPTIONS

**Allowed Headers:**
- Content-Type

---

## Rate Limiting

Currently no rate limiting in development mode.

For production deployment:
- Cloud Run default: 1000 requests per instance
- Concurrency: 80 requests per instance
- Auto-scaling handles burst traffic

---

## Session Lifecycle

### Automatic Cleanup

Sessions are automatically removed after:
- **30 minutes** of inactivity
- Manual termination via `/api/session/end`

### Cleanup Thread

Background thread runs every **5 minutes** to remove expired sessions.

---

## Example Workflows

### Complete Quick Insights Flow

```bash
# 1. Generate insights
curl -X POST http://localhost:8080/api/quick-insights \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "quick-001",
    "data": {
      "type": "table",
      "html": "<table>...</table>"
    },
    "url": "https://example.com"
  }'

# That's it! Session auto-cleans up after response.
```

### Complete Deep Analyse Flow

```bash
# 1. Start session
curl -X POST http://localhost:8080/api/session/start \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "deep-001",
    "data": {"type": "table", "html": "<table>...</table>"},
    "url": "https://example.com"
  }'

# 2. Ask questions
curl -X POST http://localhost:8080/api/deep-analyse \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "deep-001",
    "message": "What patterns do you see?"
  }'

curl -X POST http://localhost:8080/api/deep-analyse \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "deep-001",
    "message": "What is the total?"
  }'

# 3. End session
curl -X POST http://localhost:8080/api/session/end \
  -H "Content-Type: application/json" \
  -d '{"sessionId": "deep-001"}'
```

---

## Testing with JavaScript (Chrome Extension)

```javascript
// Quick Insights
async function getQuickInsights(data) {
  const response = await fetch('http://localhost:8080/api/quick-insights', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionId: crypto.randomUUID(),
      data: data,
      url: window.location.href
    })
  });
  
  const result = await response.json();
  console.log(result.insights);
}

// Deep Analyse
async function startDeepAnalysis(data) {
  const sessionId = crypto.randomUUID();
  
  // Start session
  await fetch('http://localhost:8080/api/session/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, data, url: window.location.href })
  });
  
  // Ask question
  const response = await fetch('http://localhost:8080/api/deep-analyse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionId,
      message: 'Summarize this data'
    })
  });
  
  const result = await response.json();
  console.log(result.response);
  
  // End session when done
  await fetch('http://localhost:8080/api/session/end', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId })
  });
}
```

---

## Monitoring

### Check Active Sessions

```bash
curl http://localhost:8080/health | jq '.active_sessions'
```

### View Logs (Local)

```bash
# Backend logs are written to stdout
# Check terminal where backend is running
```

### View Logs (Cloud Run)

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=revela-backend" \
  --limit 50 \
  --format json
```

---

## Performance Tips

1. **Quick Insights**: Use for one-off analysis (faster)
2. **Deep Analyse**: Use for multiple related questions (maintains context)
3. **Session Cleanup**: Always call `/api/session/end` when done
4. **Data Size**: Keep table HTML under 100KB for best performance
5. **Concurrent Requests**: Backend handles 80 concurrent sessions per instance

---

## Support

For issues or questions:
- Check backend logs for errors
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Test health endpoint: `curl http://localhost:8080/health`
- Review session creation in logs

---

**API Version:** 1.0.0  
**Last Updated:** November 10, 2025
