# 🔌 RouteWise AI API Documentation

> **Comprehensive API reference for integrating with RouteWise AI**

## 📋 Table of Contents

- [API Overview](#api-overview)
- [Authentication](#authentication)
- [Core Endpoints](#core-endpoints)
- [Request/Response Formats](#requestresponse-formats)
- [Client Libraries](#client-libraries)
- [Integration Examples](#integration-examples)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Webhooks](#webhooks)

## 🌐 API Overview

RouteWise AI provides multiple interfaces for travel planning and search functionality:

- **🌐 Web Interface**: Next.js frontend at `http://localhost:3000`
- **💻 CLI Interface**: Command-line tool for direct interaction
- **📱 Telegram Bot**: Conversational interface through Telegram
- **🔌 REST API**: HTTP endpoints for custom integrations
- **⚡ MCP Protocol**: Direct agent communication for advanced use cases

### Base URLs

| Environment | Base URL | Status |
|-------------|----------|--------|
| **Development** | `http://localhost:8000` | ✅ Active |
| **Production** | `https://api.routewise.ai` | 🚧 Coming Soon |

## 🔐 Authentication

### API Key Authentication

```http
GET /api/v1/plan
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

### Session-Based Authentication (Web)

```javascript
// Web interface uses session-based auth
fetch('/api/plan', {
  method: 'POST',
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json',
    'X-Session-ID': sessionId
  },
  body: JSON.stringify(requestData)
})
```

## 🛠️ Core Endpoints

### 1. Travel Planning

#### `POST /api/v1/plan`

Generate a comprehensive travel plan based on user requirements.

**Request:**
```json
{
  "query": "Plan a 5-day trip to Tokyo for a first-time visitor",
  "preferences": {
    "budget_range": "moderate",
    "interests": ["culture", "food", "technology"],
    "travel_style": "balanced"
  },
  "context": {
    "departure_country": "US",
    "travel_dates": {
      "start": "2024-03-15",
      "end": "2024-03-20"
    },
    "group_size": 2,
    "is_first_time": true
  },
  "options": {
    "include_flights": false,
    "include_visa_info": true,
    "include_budget": true,
    "include_checklist": true,
    "reality_first": true
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "sess_abc123",
    "trip_id": "trip_xyz789",
    "response": {
      "reality_check": {
        "insights": [
          {
            "type": "timing",
            "content": "March is cherry blossom season - expect crowds and higher prices",
            "confidence": 0.9
          }
        ]
      },
      "itinerary": {
        "days": [
          {
            "day": 1,
            "date": "2024-03-15",
            "theme": "Arrival & Tokyo Orientation",
            "activities": [
              {
                "time": "09:00",
                "activity": "Arrive at Haneda Airport",
                "duration": "2 hours",
                "location": "Haneda Airport (HND)",
                "notes": "Immigration and customs"
              }
            ]
          }
        ]
      },
      "budget": {
        "total_estimate": {
          "amount": 2500,
          "currency": "USD",
          "per_person": true
        },
        "breakdown": {
          "accommodation": 800,
          "food": 600,
          "transportation": 300,
          "activities": 500,
          "miscellaneous": 300
        }
      },
      "visa_info": {
        "required": false,
        "visa_free_days": 90,
        "requirements": ["Valid passport", "Return ticket"]
      },
      "checklist": {
        "before_travel": [
          "Book accommodation",
          "Get travel insurance",
          "Download Google Translate app"
        ],
        "packing": [
          "Comfortable walking shoes",
          "Portable charger",
          "Cash (Japan is cash-heavy)"
        ]
      }
    },
    "metadata": {
      "generated_at": "2024-01-15T10:30:00Z",
      "processing_time": 4.2,
      "agents_used": ["search", "reality_miner", "itinerary", "budget", "visa", "checklist"],
      "sources_count": 15
    }
  }
}
```

### 2. Search Only

#### `POST /api/v1/search`

Perform travel-focused search without full planning.

**Request:**
```json
{
  "query": "Best ramen shops in Shibuya Tokyo",
  "context": {
    "location": "Tokyo, Japan",
    "focus": "food"
  },
  "options": {
    "max_results": 10,
    "include_insights": true
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "results": [
      {
        "title": "Ichiran Ramen Shibuya",
        "description": "Famous tonkotsu ramen chain with individual booths",
        "url": "https://example.com/ichiran",
        "location": "Shibuya, Tokyo",
        "rating": 4.2,
        "price_range": "¥800-1200",
        "insights": [
          {
            "type": "tip",
            "content": "Order using the paper form - English available"
          }
        ]
      }
    ],
    "reality_insights": [
      {
        "type": "cost",
        "content": "Most ramen shops in Shibuya cost ¥800-1500 per bowl",
        "confidence": 0.85
      }
    ]
  }
}
```

### 3. Conversation Management

#### `POST /api/v1/chat`

Continue or modify existing travel plans through conversation.

**Request:**
```json
{
  "session_id": "sess_abc123",
  "message": "Can you make the budget more affordable?",
  "context": {
    "previous_trip_id": "trip_xyz789"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "response": "I've updated your Tokyo itinerary with budget-friendly alternatives...",
    "updated_sections": ["budget", "itinerary"],
    "changes": {
      "budget": {
        "old_total": 2500,
        "new_total": 1800,
        "savings": 700
      }
    }
  }
}
```

### 4. Session Management

#### `GET /api/v1/sessions/{session_id}`

Retrieve conversation history and context.

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "sess_abc123",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "messages": [
      {
        "id": "msg_001",
        "role": "user",
        "content": "Plan a 5-day trip to Tokyo",
        "timestamp": "2024-01-15T10:00:00Z"
      },
      {
        "id": "msg_002",
        "role": "assistant",
        "content": "I'll help you plan an amazing Tokyo trip...",
        "timestamp": "2024-01-15T10:00:15Z"
      }
    ],
    "trip_context": {
      "destinations": ["Tokyo"],
      "duration_days": 5,
      "budget_range": "moderate",
      "current_itinerary": "..."
    }
  }
}
```

## 📊 Request/Response Formats

### Standard Response Structure

All API responses follow this structure:

```json
{
  "status": "success|error",
  "data": {
    // Response data
  },
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      // Additional error context
    }
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2024-01-15T10:30:00Z",
    "processing_time": 4.2,
    "version": "1.0.0"
  }
}
```

### Data Types

#### Trip Parameters
```typescript
interface TripParameters {
  query: string;
  preferences?: {
    budget_range?: 'budget' | 'moderate' | 'luxury';
    interests?: string[];
    travel_style?: 'relaxed' | 'balanced' | 'packed';
  };
  context?: {
    departure_country?: string;
    travel_dates?: {
      start: string; // ISO date
      end: string;   // ISO date
    };
    group_size?: number;
    is_first_time?: boolean;
  };
  options?: {
    include_flights?: boolean;
    include_visa_info?: boolean;
    include_budget?: boolean;
    include_checklist?: boolean;
    reality_first?: boolean;
  };
}
```

#### Insight Object
```typescript
interface Insight {
  type: 'scam' | 'warning' | 'hack' | 'cost' | 'timing' | 'safety';
  content: string;
  confidence: number; // 0.0 to 1.0
  source?: string;
  location?: string;
}
```

## 📚 Client Libraries

### Python Client

```python
from routewise import RouteWiseClient

# Initialize client
client = RouteWiseClient(
    api_key="your_api_key",
    base_url="http://localhost:8000"
)

# Plan a trip
response = client.plan_trip(
    query="5 days in Tokyo for first-time visitor",
    preferences={
        "budget_range": "moderate",
        "interests": ["culture", "food"]
    },
    options={
        "reality_first": True,
        "include_budget": True
    }
)

print(response.itinerary)
print(response.budget)
```

### JavaScript/TypeScript Client

```typescript
import { RouteWiseClient } from '@routewise/client';

const client = new RouteWiseClient({
  apiKey: 'your_api_key',
  baseUrl: 'http://localhost:8000'
});

// Plan a trip
const response = await client.planTrip({
  query: '5 days in Tokyo for first-time visitor',
  preferences: {
    budgetRange: 'moderate',
    interests: ['culture', 'food']
  },
  options: {
    realityFirst: true,
    includeBudget: true
  }
});

console.log(response.data.itinerary);
```

### cURL Examples

```bash
# Plan a trip
curl -X POST http://localhost:8000/api/v1/plan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "query": "3 days in Paris for art lovers",
    "preferences": {
      "budget_range": "moderate",
      "interests": ["art", "culture"]
    },
    "options": {
      "reality_first": true
    }
  }'

# Search only
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "best museums in Paris",
    "options": {
      "max_results": 5,
      "include_insights": true
    }
  }'
```

## 🔧 Integration Examples

### React Integration

```tsx
import React, { useState } from 'react';
import { RouteWiseClient } from '@routewise/client';

const TripPlanner: React.FC = () => {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const client = new RouteWiseClient({
    baseUrl: process.env.REACT_APP_API_URL
  });
  
  const handlePlanTrip = async () => {
    setLoading(true);
    try {
      const result = await client.planTrip({
        query,
        options: { realityFirst: true }
      });
      setResponse(result.data);
    } catch (error) {
      console.error('Planning failed:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Describe your trip..."
      />
      <button onClick={handlePlanTrip} disabled={loading}>
        {loading ? 'Planning...' : 'Plan Trip'}
      </button>
      
      {response && (
        <div>
          <h3>Your Trip Plan</h3>
          <pre>{JSON.stringify(response, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};
```

### Express.js Middleware

```javascript
const express = require('express');
const { RouteWiseClient } = require('@routewise/client');

const app = express();
const routewise = new RouteWiseClient({
  apiKey: process.env.ROUTEWISE_API_KEY
});

// Middleware for trip planning
app.post('/plan-trip', async (req, res) => {
  try {
    const { query, preferences, options } = req.body;
    
    const response = await routewise.planTrip({
      query,
      preferences,
      options
    });
    
    res.json(response.data);
  } catch (error) {
    res.status(500).json({
      error: 'Trip planning failed',
      details: error.message
    });
  }
});
```

## ❌ Error Handling

### Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_REQUEST` | Malformed request data | 400 |
| `UNAUTHORIZED` | Invalid or missing API key | 401 |
| `RATE_LIMITED` | Too many requests | 429 |
| `AGENT_TIMEOUT` | Agent processing timeout | 504 |
| `AGENT_ERROR` | Internal agent error | 500 |
| `SEARCH_FAILED` | Search service unavailable | 503 |
| `INVALID_SESSION` | Session not found or expired | 404 |

### Error Response Format

```json
{
  "status": "error",
  "error": {
    "code": "AGENT_TIMEOUT",
    "message": "The search agent timed out while processing your request",
    "details": {
      "agent": "search_agent",
      "timeout_duration": 30,
      "retry_after": 60
    }
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Retry Strategy

```python
import time
import random
from routewise import RouteWiseClient, RouteWiseError

def plan_trip_with_retry(client, request_data, max_retries=3):
    """Plan trip with exponential backoff retry"""
    
    for attempt in range(max_retries + 1):
        try:
            return client.plan_trip(**request_data)
        except RouteWiseError as e:
            if e.code in ['RATE_LIMITED', 'AGENT_TIMEOUT'] and attempt < max_retries:
                # Exponential backoff with jitter
                delay = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
                continue
            raise
    
    raise RouteWiseError("Max retries exceeded")
```

## 🚦 Rate Limiting

### Rate Limits

| Endpoint | Rate Limit | Window |
|----------|------------|--------|
| `/api/v1/plan` | 10 requests | 1 minute |
| `/api/v1/search` | 30 requests | 1 minute |
| `/api/v1/chat` | 60 requests | 1 minute |
| `/api/v1/sessions/*` | 100 requests | 1 minute |

### Rate Limit Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1642248000
X-RateLimit-Window: 60
```

### Rate Limit Exceeded Response

```json
{
  "status": "error",
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Try again in 45 seconds.",
    "details": {
      "limit": 10,
      "window": 60,
      "reset_at": "2024-01-15T10:31:00Z"
    }
  }
}
```

## 🔔 Webhooks

### Webhook Events

| Event | Description | Payload |
|-------|-------------|----------|
| `trip.planned` | Trip planning completed | Trip data |
| `trip.updated` | Trip modified via chat | Updated sections |
| `search.completed` | Search request finished | Search results |
| `agent.failed` | Agent processing failed | Error details |

### Webhook Configuration

```json
{
  "url": "https://your-app.com/webhooks/routewise",
  "events": ["trip.planned", "trip.updated"],
  "secret": "your_webhook_secret"
}
```

### Webhook Payload Example

```json
{
  "event": "trip.planned",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "session_id": "sess_abc123",
    "trip_id": "trip_xyz789",
    "user_query": "5 days in Tokyo",
    "response": {
      // Full trip response
    }
  },
  "signature": "sha256=abc123..."
}
```

### Webhook Verification

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    """Verify webhook signature"""
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## 🔧 Development & Testing

### Local Development Setup

```bash
# Start the API server
cd routewise-ai
python -m src.main --mode api --port 8000

# Test endpoints
curl http://localhost:8000/api/v1/health
```

### API Testing

```python
# tests/test_api.py
import pytest
from routewise import RouteWiseClient

@pytest.fixture
def client():
    return RouteWiseClient(base_url="http://localhost:8000")

def test_plan_trip(client):
    response = client.plan_trip(
        query="2 days in Paris",
        options={"reality_first": True}
    )
    
    assert response.status == "success"
    assert "itinerary" in response.data
    assert len(response.data.itinerary.days) == 2

def test_search_only(client):
    response = client.search(
        query="best cafes in Paris",
        options={"max_results": 5}
    )
    
    assert response.status == "success"
    assert len(response.data.results) <= 5
```

---

<div align="center">
  <strong>Build amazing travel experiences with RouteWise AI</strong>
  <br>
  <sub>Intelligent travel planning through powerful APIs</sub>
</div>