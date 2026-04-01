# Customer AI - API Reference

## Overview

The Customer AI API provides AI-powered customer service capabilities for businesses. It enables natural language conversations, intent analysis, sentiment detection, and intelligent escalation.

**Base URL (Development)**: `http://localhost:8000`  
**Base URL (Production)**: `https://api.ndara.ai/customer-ai`  
**API Version**: `v1`  
**Authentication**: API Key (Header: `X-API-Key`)

---

## Authentication

All API requests require an API key in the request header:

```http
X-API-Key: your_api_key_here
```

**Obtaining an API Key:**
- Contact your account manager
- Generate from the Business Owner Dashboard
- API keys are business-specific

---

## Endpoints

### 1. Health Check

**GET** `/health`

Check API service health and status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-10T12:00:00Z",
  "details": {
    "components": {
      "data_ingestion": true,
      "industry_classifier": true,
      "conversation_manager": true,
      "knowledge_base": true,
      "vector_store": true
    }
  }
}
```

**Status Codes:**
- `200 OK`: Service is healthy
- `503 Service Unavailable`: Service is down

---

### 2. Onboard Business

**POST** `/api/v1/onboard`

Train AI on business data for personalized customer service.

**Request Body:**
```json
{
  "business_id": "biz_12345",
  "business_data": {
    "business_profile": {
      "business_name": "Mario's Restaurant",
      "industry": "restaurants",
      "description": "Authentic Italian cuisine in Lagos",
      "contact_info": {
        "email": "info@marios.com",
        "phone": "+234-xxx-xxxx",
        "address": "123 Victoria Island, Lagos"
      },
      "operating_hours": {
        "monday": "10:00-22:00",
        "tuesday": "10:00-22:00",
        "wednesday": "10:00-22:00",
        "thursday": "10:00-22:00",
        "friday": "10:00-23:00",
        "saturday": "10:00-23:00",
        "sunday": "12:00-22:00"
      }
    },
    "products_services": [
      {
        "name": "Margherita Pizza",
        "description": "Classic pizza with tomato, mozzarella, and basil",
        "price": 5000,
        "category": "pizza",
        "availability": true
      }
    ],
    "faqs": [
      {
        "question": "Do you offer delivery?",
        "answer": "Yes, we deliver within 10km radius",
        "category": "delivery"
      }
    ]
  }
}
```

**Response:**
```json
{
  "success": true,
  "business_id": "biz_12345",
  "industry": "restaurants",
  "confidence": 0.98,
  "training_result": {
    "success": true,
    "embeddings_created": 45,
    "faqs_indexed": 12
  },
  "generated_faqs": [
    {
      "question": "What are your operating hours?",
      "answer": "We're open Monday-Thursday 10AM-10PM...",
      "category": "hours"
    }
  ],
  "ai_context": {
    "personality": "friendly_professional",
    "tone": "warm_welcoming",
    "expertise_areas": ["italian_cuisine", "pizza", "pasta"]
  },
  "model_info": {
    "type": "base_model",
    "model_id": "gpt-4-turbo-preview"
  }
}
```

**Status Codes:**
- `200 OK`: Business onboarded successfully
- `400 Bad Request`: Invalid business data
- `409 Conflict`: Business already exists

**Error Example:**
```json
{
  "success": false,
  "error": "Industry classification failed: insufficient data",
  "validation_result": {
    "is_valid": false,
    "errors": ["Missing required field: business_name"]
  }
}
```

---

### 3. Chat (Process Customer Message)

**POST** `/api/v1/chat?business_id={business_id}`

Process customer message and generate AI response.

**Query Parameters:**
- `business_id` (required): Business identifier

**Request Body:**
```json
{
  "message": "Do you have vegetarian options?",
  "customer_id": "cust_67890",
  "context": {
    "conversation_id": "conv_abc123",
    "channel": "whatsapp",
    "is_first_interaction": false,
    "is_new_day": false,
    "conversation_history": [
      { "role": "customer", "message": "Hi" },
      { "role": "ai", "message": "Hello! How can I help?" }
    ]
  }
}
```

**Context (greetings and conversational memory):**
- `conversation_id` — Same ID for the whole chat (required for scoping).
- `channel` — e.g. `"whatsapp"`, `"voice"`.
- `is_first_interaction` — `true` only when this customer has never chatted before → AI gives a short introduction, then answers.
- `is_new_day` — `true` when it’s the first message today (or first after 24h) → AI gives a time-of-day greeting, then answers.
- `conversation_history` — Prior turns only (not the current `message`). Each item: `{ "role": "customer" | "ai", "message": "..." }`. Send on every request so the AI can answer follow-ups (e.g. "Yes", "Yes pls"). Can be full history or last N turns.

**Response:**
```json
{
  "success": true,
  "response": "Yes! At Mario's, we have several delicious vegetarian options including our Margherita Pizza, Pasta Primavera, and Caprese Salad. All are made fresh daily. Would you like to hear more about any of these dishes?",
  "intent": {
    "type": "product_inquiry",
    "confidence": 0.92,
    "entities": {
      "dietary_preference": "vegetarian",
      "category": "menu_items"
    }
  },
  "sentiment": {
    "sentiment": "neutral",
    "score": 0.05,
    "confidence": 0.88
  },
  "escalation_required": false,
  "quality_score": 0.87,
  "conversation_analytics": {
    "total_turns": 3,
    "conversation_stage": "product_exploration",
    "engagement_level": "medium"
  },
  "proactive_suggestions": {
    "upsell_opportunity": {
      "has_opportunity": true,
      "suggested_products": ["Tiramisu", "Wine Pairing"],
      "confidence": 0.75
    },
    "abandonment_risk": {
      "at_risk": false,
      "risk_level": "low"
    }
  },
  "token_usage": {
    "prompt_tokens": 245,
    "completion_tokens": 68,
    "total_tokens": 313
  }
}
```

**Status Codes:**
- `200 OK`: Message processed successfully
- `400 Bad Request`: Invalid request format
- `404 Not Found`: Business not found
- `429 Too Many Requests`: Rate limit exceeded

**Advanced Features in Response:**

1. **Intent Analysis**: Detected customer intent with confidence
2. **Sentiment Analysis**: Customer mood detection
3. **Escalation Flag**: Automatic escalation detection
4. **Quality Score**: AI self-evaluation (0-1)
5. **Proactive Suggestions**: Upsell opportunities, abandonment risk
6. **Structured Data**: Extracted entities for backend processing

---

### 4. Extract Intent

**POST** `/api/v1/extract-intent?business_id={business_id}`

Extract customer intent without generating response.

**Request Body:**
```json
{
  "message": "I want to book a table for 4 people tomorrow at 7pm"
}
```

**Response:**
```json
{
  "success": true,
  "intent": "appointment_booking",
  "confidence": 0.95,
  "entities": {
    "service_type": "table_reservation",
    "party_size": 4,
    "preferred_datetime": "2025-10-11T19:00:00",
    "date": "tomorrow",
    "time": "7pm"
  },
  "metadata": {
    "urgency": "normal",
    "requires_confirmation": true
  }
}
```

**Use Case**: Backend systems can use this to trigger specific workflows (e.g., calendar booking) without full AI conversation.

---

### 5. Analyze Sentiment

**POST** `/api/v1/analyze-sentiment?business_id={business_id}`

Analyze sentiment of customer message.

**Request Body:**
```json
{
  "message": "This is absolutely terrible! I've been waiting for 2 hours!"
}
```

**Response:**
```json
{
  "success": true,
  "sentiment": "negative",
  "score": -0.89,
  "confidence": 0.96,
  "severity": "high",
  "escalation_recommended": true,
  "indicators": ["terrible", "waiting", "2 hours"],
  "suggested_action": "Immediate escalation to manager"
}
```

**Sentiment Scale:**
- `positive`: score > 0.3
- `neutral`: -0.3 ≤ score ≤ 0.3
- `negative`: score < -0.3

---

### 6. Process Feedback

**POST** `/api/v1/feedback?business_id={business_id}`

Submit customer feedback for AI learning.

**Request Body:**
```json
{
  "customer_id": "cust_67890",
  "rating": 5,
  "feedback_text": "Very helpful and quick response!"
}
```

**Response:**
```json
{
  "success": true,
  "learning_result": {
    "feedback_recorded": true,
    "model_updated": true,
    "confidence_adjustment": 0.02
  },
  "message": "Feedback processed for AI learning"
}
```

**Rating Scale**: 1-5 (1 = Poor, 5 = Excellent)

---

### 7. Register Escalation

**POST** `/api/v1/escalate?business_id={business_id}`

Register an escalation to human/business owner. Backend calls this after detecting `escalation_required` in chat response. Returns `escalation_id`, `recommended_action`, and `context_for_agent` for routing.

**Request Body:**
```json
{
  "conversation_id": "conv_abc123",
  "customer_id": "cust_67890",
  "reason": "complaint_severity_high",
  "severity": "high",
  "context_summary": "Customer frustrated with delivery delay. Third complaint this week.",
  "conversation_history": [
    {"role": "customer", "message": "Where is my order?"},
    {"role": "ai", "message": "Let me check that for you..."}
  ],
  "customer_message": "This is the third time! I want a refund!",
  "ai_response": "I understand your frustration. Let me connect you with our manager."
}
```

**Response:**
```json
{
  "success": true,
  "escalation_id": "esc_20251010120000_biz_12345",
  "recommended_action": "Connect with customer relations manager within 1 hour",
  "context_for_agent": "Customer frustrated with delivery delay. Third complaint this week.\n\nConversation excerpt:\ncustomer: Where is my order?\nai: Let me check that for you..."
}
```

**Escalation Flow:**
1. Chat response includes `escalation_required: true` and `escalation` payload (severity, context_summary, suggested_action).
2. Backend decides to escalate and calls this endpoint to register.
3. Backend routes to business owner/support using `recommended_action` and `context_for_agent`.
4. AI does not send notifications; backend owns routing and notifications.

**Status Codes:**
- `200 OK`: Escalation registered successfully
- `400 Bad Request`: Invalid request format
- `500 Internal Server Error`: Registration failed

---

### 8. Get Model Status

**GET** `/api/v1/model-status?business_id={business_id}`

Get AI model status and training information.

**Response:**
```json
{
  "success": true,
  "business_id": "biz_12345",
  "industry": "restaurants",
  "model_type": "industry_model",
  "model_id": "ft:gpt-4-turbo:restaurants-v2",
  "base_model": "gpt-4-turbo-preview",
  "data_completeness": 0.92,
  "last_updated": "2025-10-10T08:30:00Z",
  "training_status": "completed",
  "performance_metrics": {
    "avg_confidence": 0.89,
    "avg_quality_score": 0.85,
    "escalation_rate": 0.08
  }
}
```

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": "Error description",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "specific_field",
    "message": "Additional context"
  }
}
```

### Common Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `INVALID_API_KEY` | API key is invalid or missing | Check X-API-Key header |
| `BUSINESS_NOT_FOUND` | Business ID not found | Onboard business first |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Wait and retry with exponential backoff |
| `INVALID_REQUEST` | Request format invalid | Check request schema |
| `MODEL_NOT_TRAINED` | AI not trained yet | Complete onboarding first |
| `INTERNAL_ERROR` | Server error | Contact support |

---

## Rate Limiting

- **Standard**: 100 requests/minute per business
- **Premium**: 1000 requests/minute per business
- **Headers**:
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

**Exceeded Response:**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

---

## Code Examples

### Python

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "http://localhost:8000"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Chat with AI
response = requests.post(
    f"{BASE_URL}/api/v1/chat",
    params={"business_id": "biz_12345"},
    headers=headers,
    json={
        "message": "Do you deliver to Lekki?",
        "customer_id": "cust_001"
    }
)

result = response.json()
print(result['response'])
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_KEY = 'your_api_key';
const BASE_URL = 'http://localhost:8000';

const headers = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json'
};

// Chat with AI
async function chat(businessId, message, customerId) {
  const response = await axios.post(
    `${BASE_URL}/api/v1/chat`,
    {
      message: message,
      customer_id: customerId
    },
    {
      headers: headers,
      params: { business_id: businessId }
    }
  );
  
  return response.data;
}

// Usage
chat('biz_12345', 'What are your hours?', 'cust_001')
  .then(result => console.log(result.response))
  .catch(error => console.error(error));
```

### cURL

```bash
# Onboard Business
curl -X POST http://localhost:8000/api/v1/onboard \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "biz_12345",
    "business_data": {
      "business_profile": {
        "business_name": "Test Business",
        "industry": "restaurants"
      }
    }
  }'

# Chat
curl -X POST "http://localhost:8000/api/v1/chat?business_id=biz_12345" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type": "application/json" \
  -d '{
    "message": "Hello",
    "customer_id": "cust_001"
  }'
```

---

## Webhooks (Optional)

For async operations, register a webhook URL to receive callbacks.

**Webhook Payload:**
```json
{
  "event": "conversation.escalated",
  "business_id": "biz_12345",
  "timestamp": "2025-10-10T12:00:00Z",
  "data": {
    "conversation_id": "conv_abc123",
    "customer_id": "cust_67890",
    "severity": "high",
    "context_summary": "Customer complaint about delivery delay"
  }
}
```

**Event Types:**
- `conversation.escalated`: Escalation triggered
- `feedback.received`: Customer feedback submitted
- `quality.threshold_breach`: Quality score below threshold
- `model.updated`: AI model updated

---

## Best Practices

1. **Cache Business Data**: Store business details locally to reduce onboarding calls
2. **Handle Timeouts**: Set 30-second timeout for API calls
3. **Retry Logic**: Use exponential backoff for retries (max 3 attempts)
4. **Monitor Quality**: Track quality_score in responses
5. **Escalate Properly**: Honor escalation_required flag
6. **Store Context**: Use conversation_id for multi-turn conversations
7. **Rate Limiting**: Implement client-side rate limiting
8. **Error Logging**: Log all error responses for debugging

---

## Support

- **Documentation**: https://docs.ndara.ai
- **API Status**: https://status.ndara.ai
- **Support Email**: api-support@ndara.ai
- **Developer Slack**: #api-support

---

**Version**: 1.0.0  
**Last Updated**: October 10, 2025  
**Changelog**: See [CHANGELOG.md](./CHANGELOG.md)

