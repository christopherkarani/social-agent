# API Documentation

The Bluesky Crypto Agent provides REST API endpoints for configuration management, monitoring, and control. This document describes all available endpoints and their usage.

## Base URL

When running locally with Docker:
```
http://localhost:8080/api/v1
```

## Authentication

Currently, the API uses basic authentication or API key authentication (configurable).

### API Key Authentication
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8080/api/v1/status
```

### Basic Authentication
```bash
curl -u username:password http://localhost:8080/api/v1/status
```

## Endpoints

### Health and Status

#### GET /health
Check if the agent is running and healthy.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime": 3600,
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK` - Agent is healthy
- `503 Service Unavailable` - Agent is unhealthy

**Example:**
```bash
curl http://localhost:8080/api/v1/health
```

#### GET /status
Get detailed status information about the agent.

**Response:**
```json
{
  "agent": {
    "status": "running",
    "last_execution": "2024-01-15T10:25:00Z",
    "next_execution": "2024-01-15T11:00:00Z",
    "execution_count": 48,
    "uptime_seconds": 3600
  },
  "scheduler": {
    "status": "active",
    "interval_minutes": 30,
    "last_run": "2024-01-15T10:25:00Z",
    "next_run": "2024-01-15T10:55:00Z"
  },
  "apis": {
    "perplexity": {
      "status": "connected",
      "last_request": "2024-01-15T10:25:00Z",
      "request_count": 48,
      "error_count": 2
    },
    "bluesky": {
      "status": "connected",
      "last_post": "2024-01-15T10:25:00Z",
      "post_count": 46,
      "error_count": 1
    }
  },
  "content": {
    "posts_today": 46,
    "filtered_count": 12,
    "duplicate_count": 3,
    "avg_engagement_score": 0.78
  }
}
```

**Status Codes:**
- `200 OK` - Status retrieved successfully

**Example:**
```bash
curl http://localhost:8080/api/v1/status
```

### Configuration Management

#### GET /config
Get current agent configuration.

**Response:**
```json
{
  "posting_interval_minutes": 30,
  "max_execution_time_minutes": 25,
  "max_post_length": 300,
  "content_themes": ["Bitcoin", "Ethereum", "DeFi", "NFTs"],
  "min_engagement_score": 0.7,
  "duplicate_threshold": 0.8,
  "max_retries": 3,
  "log_level": "INFO"
}
```

**Status Codes:**
- `200 OK` - Configuration retrieved successfully

**Example:**
```bash
curl http://localhost:8080/api/v1/config
```

#### PUT /config
Update agent configuration.

**Request Body:**
```json
{
  "posting_interval_minutes": 45,
  "min_engagement_score": 0.8,
  "content_themes": ["Bitcoin", "Ethereum", "DeFi", "NFTs", "Web3"]
}
```

**Response:**
```json
{
  "message": "Configuration updated successfully",
  "updated_fields": ["posting_interval_minutes", "min_engagement_score", "content_themes"],
  "restart_required": true
}
```

**Status Codes:**
- `200 OK` - Configuration updated successfully
- `400 Bad Request` - Invalid configuration values
- `422 Unprocessable Entity` - Validation errors

**Example:**
```bash
curl -X PUT \
  -H "Content-Type: application/json" \
  -d '{"posting_interval_minutes": 45}' \
  http://localhost:8080/api/v1/config
```

#### POST /config/validate
Validate configuration without applying changes.

**Request Body:**
```json
{
  "posting_interval_minutes": 15,
  "max_execution_time_minutes": 20
}
```

**Response:**
```json
{
  "valid": false,
  "errors": [
    {
      "field": "max_execution_time_minutes",
      "message": "Must be less than posting_interval_minutes"
    }
  ],
  "warnings": [
    {
      "field": "posting_interval_minutes",
      "message": "Very frequent posting may hit rate limits"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Validation completed
- `400 Bad Request` - Invalid request format

### Agent Control

#### POST /agent/start
Start the agent if it's stopped.

**Response:**
```json
{
  "message": "Agent started successfully",
  "status": "running",
  "next_execution": "2024-01-15T11:00:00Z"
}
```

**Status Codes:**
- `200 OK` - Agent started successfully
- `409 Conflict` - Agent is already running

**Example:**
```bash
curl -X POST http://localhost:8080/api/v1/agent/start
```

#### POST /agent/stop
Stop the agent.

**Response:**
```json
{
  "message": "Agent stopped successfully",
  "status": "stopped",
  "last_execution": "2024-01-15T10:25:00Z"
}
```

**Status Codes:**
- `200 OK` - Agent stopped successfully
- `409 Conflict` - Agent is already stopped

**Example:**
```bash
curl -X POST http://localhost:8080/api/v1/agent/stop
```

#### POST /agent/restart
Restart the agent.

**Response:**
```json
{
  "message": "Agent restarted successfully",
  "status": "running",
  "next_execution": "2024-01-15T11:00:00Z"
}
```

**Status Codes:**
- `200 OK` - Agent restarted successfully

**Example:**
```bash
curl -X POST http://localhost:8080/api/v1/agent/restart
```

#### POST /agent/execute
Trigger immediate execution of the agent workflow.

**Request Body (optional):**
```json
{
  "skip_schedule": true,
  "force_post": false
}
```

**Response:**
```json
{
  "message": "Execution triggered successfully",
  "execution_id": "exec_1642248000",
  "status": "running",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

**Status Codes:**
- `200 OK` - Execution triggered successfully
- `409 Conflict` - Agent is already executing
- `503 Service Unavailable` - Agent is not available

**Example:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"skip_schedule": true}' \
  http://localhost:8080/api/v1/agent/execute
```

### Content Management

#### GET /content/recent
Get recent posts and content.

**Query Parameters:**
- `limit` (optional): Number of posts to return (default: 10, max: 100)
- `include_filtered` (optional): Include filtered content (default: false)

**Response:**
```json
{
  "posts": [
    {
      "id": "post_1642248000",
      "content": "🚀 Bitcoin breaks $50K resistance! The bulls are back in town. #Bitcoin #Crypto #BTC",
      "timestamp": "2024-01-15T10:25:00Z",
      "engagement_score": 0.85,
      "source_news": {
        "headline": "Bitcoin Surges Past $50,000 Mark",
        "source": "CoinDesk"
      },
      "bluesky_post_id": "at://did:plc:example/app.bsky.feed.post/3k2a4b5c6d7e8f9g",
      "status": "posted"
    }
  ],
  "filtered_content": [
    {
      "id": "filtered_1642247000",
      "content": "Bitcoin news update...",
      "timestamp": "2024-01-15T10:15:00Z",
      "filter_reason": "duplicate_content",
      "similarity_score": 0.92
    }
  ],
  "total_count": 46,
  "filtered_count": 12
}
```

**Status Codes:**
- `200 OK` - Content retrieved successfully

**Example:**
```bash
curl "http://localhost:8080/api/v1/content/recent?limit=5&include_filtered=true"
```

#### GET /content/stats
Get content statistics.

**Query Parameters:**
- `period` (optional): Time period (hour, day, week, month) (default: day)

**Response:**
```json
{
  "period": "day",
  "stats": {
    "total_posts": 46,
    "successful_posts": 44,
    "filtered_posts": 12,
    "duplicate_posts": 3,
    "failed_posts": 2,
    "avg_engagement_score": 0.78,
    "top_themes": [
      {"theme": "Bitcoin", "count": 18},
      {"theme": "Ethereum", "count": 12},
      {"theme": "DeFi", "count": 8}
    ]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Statistics retrieved successfully

**Example:**
```bash
curl "http://localhost:8080/api/v1/content/stats?period=week"
```

#### DELETE /content/history
Clear content history (affects duplicate detection).

**Request Body (optional):**
```json
{
  "keep_recent": 10
}
```

**Response:**
```json
{
  "message": "Content history cleared successfully",
  "removed_count": 40,
  "kept_count": 10
}
```

**Status Codes:**
- `200 OK` - History cleared successfully

**Example:**
```bash
curl -X DELETE \
  -H "Content-Type: application/json" \
  -d '{"keep_recent": 5}' \
  http://localhost:8080/api/v1/content/history
```

### Monitoring and Logs

#### GET /logs
Get recent log entries.

**Query Parameters:**
- `level` (optional): Log level filter (DEBUG, INFO, WARNING, ERROR)
- `limit` (optional): Number of entries (default: 100, max: 1000)
- `since` (optional): ISO timestamp to get logs since

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2024-01-15T10:25:00Z",
      "level": "INFO",
      "message": "Successfully posted content to Bluesky",
      "component": "bluesky_social_tool",
      "execution_id": "exec_1642248000"
    },
    {
      "timestamp": "2024-01-15T10:24:30Z",
      "level": "DEBUG",
      "message": "Generated content with engagement score 0.85",
      "component": "content_generation_tool",
      "execution_id": "exec_1642248000"
    }
  ],
  "total_count": 1250,
  "filtered_count": 100
}
```

**Status Codes:**
- `200 OK` - Logs retrieved successfully

**Example:**
```bash
curl "http://localhost:8080/api/v1/logs?level=ERROR&limit=50"
```

#### GET /metrics
Get performance metrics.

**Response:**
```json
{
  "performance": {
    "avg_execution_time_seconds": 45.2,
    "success_rate": 0.96,
    "api_response_times": {
      "perplexity_avg_ms": 1200,
      "bluesky_avg_ms": 800
    }
  },
  "resource_usage": {
    "memory_usage_mb": 256,
    "cpu_usage_percent": 15.5
  },
  "api_stats": {
    "perplexity": {
      "requests_today": 48,
      "errors_today": 2,
      "rate_limit_hits": 0
    },
    "bluesky": {
      "posts_today": 46,
      "errors_today": 1,
      "rate_limit_hits": 0
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Metrics retrieved successfully

**Example:**
```bash
curl http://localhost:8080/api/v1/metrics
```

### Webhook Endpoints

#### POST /webhooks/content-posted
Webhook called after successful content posting.

**Payload:**
```json
{
  "event": "content_posted",
  "timestamp": "2024-01-15T10:25:00Z",
  "data": {
    "post_id": "post_1642248000",
    "content": "🚀 Bitcoin breaks $50K resistance!",
    "bluesky_post_id": "at://did:plc:example/app.bsky.feed.post/3k2a4b5c6d7e8f9g",
    "engagement_score": 0.85
  }
}
```

#### POST /webhooks/error-occurred
Webhook called when errors occur.

**Payload:**
```json
{
  "event": "error_occurred",
  "timestamp": "2024-01-15T10:25:00Z",
  "data": {
    "error_type": "api_error",
    "component": "bluesky_social_tool",
    "message": "Failed to authenticate with Bluesky API",
    "execution_id": "exec_1642248000"
  }
}
```

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request
```json
{
  "error": "bad_request",
  "message": "Invalid request format",
  "details": {
    "field": "posting_interval_minutes",
    "issue": "Must be a positive integer"
  }
}
```

### 401 Unauthorized
```json
{
  "error": "unauthorized",
  "message": "Invalid API key or credentials"
}
```

### 404 Not Found
```json
{
  "error": "not_found",
  "message": "Endpoint not found"
}
```

### 409 Conflict
```json
{
  "error": "conflict",
  "message": "Agent is already running"
}
```

### 422 Unprocessable Entity
```json
{
  "error": "validation_error",
  "message": "Configuration validation failed",
  "errors": [
    {
      "field": "max_execution_time_minutes",
      "message": "Must be less than posting_interval_minutes"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "error": "internal_error",
  "message": "An unexpected error occurred",
  "request_id": "req_1642248000"
}
```

### 503 Service Unavailable
```json
{
  "error": "service_unavailable",
  "message": "Agent is currently unavailable"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Rate Limit**: 100 requests per minute per IP
- **Headers**: 
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

**Rate Limit Exceeded Response:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests",
  "retry_after": 60
}
```

## SDK Examples

### Python SDK Example

```python
import requests
import json

class BlueskyCryptoAgentAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
    
    def get_status(self):
        response = requests.get(f"{self.base_url}/status", headers=self.headers)
        return response.json()
    
    def update_config(self, config):
        response = requests.put(
            f"{self.base_url}/config", 
            headers=self.headers,
            data=json.dumps(config)
        )
        return response.json()
    
    def trigger_execution(self):
        response = requests.post(f"{self.base_url}/agent/execute", headers=self.headers)
        return response.json()

# Usage
api = BlueskyCryptoAgentAPI("http://localhost:8080/api/v1", "your-api-key")
status = api.get_status()
print(f"Agent status: {status['agent']['status']}")
```

### JavaScript SDK Example

```javascript
class BlueskyCryptoAgentAPI {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.headers = {
            'X-API-Key': apiKey,
            'Content-Type': 'application/json'
        };
    }
    
    async getStatus() {
        const response = await fetch(`${this.baseUrl}/status`, {
            headers: this.headers
        });
        return await response.json();
    }
    
    async updateConfig(config) {
        const response = await fetch(`${this.baseUrl}/config`, {
            method: 'PUT',
            headers: this.headers,
            body: JSON.stringify(config)
        });
        return await response.json();
    }
    
    async triggerExecution() {
        const response = await fetch(`${this.baseUrl}/agent/execute`, {
            method: 'POST',
            headers: this.headers
        });
        return await response.json();
    }
}

// Usage
const api = new BlueskyCryptoAgentAPI('http://localhost:8080/api/v1', 'your-api-key');
api.getStatus().then(status => {
    console.log(`Agent status: ${status.agent.status}`);
});
```

### cURL Examples

```bash
# Get agent status
curl -H "X-API-Key: your-api-key" \
     http://localhost:8080/api/v1/status

# Update configuration
curl -X PUT \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"posting_interval_minutes": 45}' \
     http://localhost:8080/api/v1/config

# Trigger immediate execution
curl -X POST \
     -H "X-API-Key: your-api-key" \
     http://localhost:8080/api/v1/agent/execute

# Get recent logs with error level
curl -H "X-API-Key: your-api-key" \
     "http://localhost:8080/api/v1/logs?level=ERROR&limit=20"

# Get content statistics for the week
curl -H "X-API-Key: your-api-key" \
     "http://localhost:8080/api/v1/content/stats?period=week"
```

## Security Considerations

1. **API Key Management**: Store API keys securely, rotate regularly
2. **HTTPS**: Always use HTTPS in production
3. **Rate Limiting**: Respect rate limits to avoid blocking
4. **Input Validation**: Validate all input data
5. **Error Handling**: Don't expose sensitive information in errors
6. **Logging**: Avoid logging sensitive data like API keys

## Monitoring Integration

### Prometheus Metrics

The API exposes Prometheus-compatible metrics at `/metrics`:

```
# HELP bluesky_agent_posts_total Total number of posts created
# TYPE bluesky_agent_posts_total counter
bluesky_agent_posts_total{status="success"} 46
bluesky_agent_posts_total{status="filtered"} 12
bluesky_agent_posts_total{status="failed"} 2

# HELP bluesky_agent_execution_duration_seconds Time spent executing workflows
# TYPE bluesky_agent_execution_duration_seconds histogram
bluesky_agent_execution_duration_seconds_bucket{le="30"} 42
bluesky_agent_execution_duration_seconds_bucket{le="60"} 48
bluesky_agent_execution_duration_seconds_bucket{le="+Inf"} 48
```

### Health Check Integration

Use the `/health` endpoint for:
- Docker health checks
- Load balancer health checks
- Monitoring system checks
- Kubernetes liveness/readiness probes