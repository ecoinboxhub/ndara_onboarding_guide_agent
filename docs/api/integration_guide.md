# ndara.ai Integration Guide

## Services Overview

The ndara.ai platform consists of core AI services:

1. **Customer AI** - AI-powered customer service (Port 8000)
2. **Business Owner AI** - Business intelligence and analytics (Port 8001)

**Note**: Invoice Generator and Inventory Management are handled by backend services (Ports 8004 and 8005 respectively).

## Quick Start (5 Minutes)

Get your first AI response in 5 minutes.

### Step 1: Get API Credentials
```bash
# Contact your account manager or generate from dashboard
API_KEY="your_api_key_here"
BUSINESS_ID="your_business_id"
```

### Step 2: Onboard Your Business
```bash
curl -X POST http://localhost:8000/api/v1/onboard \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "'$BUSINESS_ID'",
    "business_data": {
      "business_profile": {
        "business_name": "My Business",
        "industry": "restaurants",
        "description": "Great food and service"
      },
      "products_services": [
        {"name": "Service A", "price": 5000, "description": "Our main service"}
      ]
    }
  }'
```

### Step 3: Send Your First Message
```bash
curl -X POST "http://localhost:8000/api/v1/chat?business_id=$BUSINESS_ID" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are your prices?",
    "customer_id": "test_customer"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "response": "At My Business, our Service A is priced at ₦5,000..."
}
```

✅ **Success!** You've integrated ndara.ai

---

## Authentication Setup

### API Key Management

**Obtaining API Keys:**
1. Log into Business Owner Dashboard
2. Navigate to Settings → API Keys
3. Click "Generate New Key"
4. Save securely (shown only once)

**Using API Keys:**
```http
X-API-Key: your_api_key_here
```

**Security Best Practices:**
- Never commit API keys to version control
- Use environment variables
- Rotate keys every 90 days
- Use different keys for dev/staging/production
- Monitor API key usage

### Environment Variables

```bash
# .env file
NDARA_API_KEY=your_api_key
NDARA_BUSINESS_ID=your_business_id
NDARA_API_URL=https://api.ndara.ai
```

---

## SDK Installation

### Python SDK

```bash
pip install ndara-ai-sdk
```

```python
from ndara import NdaraAI

client = NdaraAI(
    api_key="your_api_key",
    business_id="your_business_id"
)

# Chat
response = client.chat("What are your hours?", customer_id="cust_001")
print(response.message)

# Analyze sales
analysis = client.analyze_sales(
    conversations=conversations,
    sales_data=sales_data
)
print(analysis.key_metrics)
```

### JavaScript SDK

```bash
npm install @ndara/ai-sdk
```

```javascript
const { NdaraAI } = require('@ndara/ai-sdk');

const client = new NdaraAI({
  apiKey: 'your_api_key',
  businessId: 'your_business_id'
});

// Chat
const response = await client.chat({
  message: 'What are your hours?',
  customerId: 'cust_001'
});

console.log(response.message);
```

---

## Error Handling Best Practices

### Retry Logic with Exponential Backoff

```python
import time
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def create_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,  # 0.5s, 1s, 2s
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

session = create_session()

# Make request with automatic retries
response = session.post(
    'https://api.ndara.ai/api/v1/chat',
    headers={'X-API-Key': API_KEY},
    json={'message': 'Hello'}
)
```

### Comprehensive Error Handling

```python
try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    result = response.json()
    
    if not result.get('success'):
        handle_api_error(result)
    
    return result

except requests.exceptions.Timeout:
    # Request took too long
    logger.error("API request timeout")
    return fallback_response()

except requests.exceptions.ConnectionError:
    # Network problem
    logger.error("Connection error")
    return fallback_response()

except requests.exceptions.HTTPError as e:
    # HTTP error (4xx, 5xx)
    if e.response.status_code == 429:
        # Rate limited
        retry_after = int(e.response.headers.get('Retry-After', 60))
        time.sleep(retry_after)
        return retry_request()
    elif e.response.status_code >= 500:
        # Server error - retry
        return retry_with_backoff()
    else:
        # Client error - don't retry
        logger.error(f"HTTP error: {e}")
        return None

except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return None
```

---

## Testing

### Sandbox Environment

**Sandbox URL**: `https://sandbox-api.ndara.ai`

```python
# Use sandbox for testing
client = NdaraAI(
    api_key="test_api_key",
    business_id="test_business",
    base_url="https://sandbox-api.ndara.ai"
)
```

### Test Data

```json
{
  "test_business_id": "test_biz_001",
  "test_customer_id": "test_cust_001",
  "test_api_key": "test_key_xxxxx"
}
```

### Unit Testing

```python
import unittest
from unittest.mock import patch, Mock

class TestNdaraIntegration(unittest.TestCase):
    
    @patch('requests.post')
    def test_chat_success(self, mock_post):
        # Mock successful response
        mock_post.return_value.json.return_value = {
            'success': True,
            'response': 'Hello!'
        }
        
        response = chat("Hi", "cust_001")
        self.assertTrue(response['success'])
        self.assertEqual(response['response'], 'Hello!')
    
    @patch('requests.post')
    def test_chat_error_handling(self, mock_post):
        # Mock error response
        mock_post.side_effect = requests.exceptions.Timeout()
        
        response = chat("Hi", "cust_001")
        # Should return fallback
        self.assertIsNotNone(response)
```

---

## Production Checklist

Before going live, ensure:

- [ ] API keys rotated from development keys
- [ ] Error handling implemented with retries
- [ ] Logging configured (errors, API calls, responses)
- [ ] Rate limiting implemented client-side
- [ ] Timeout set to 30 seconds
- [ ] Fallback responses configured
- [ ] Monitoring and alerts set up
- [ ] Load testing completed
- [ ] Security review completed
- [ ] Documentation reviewed
- [ ] Team trained on integration
- [ ] Rollback plan prepared
- [ ] Support contacts saved

---

## Monitoring

### Health Checks

```python
import requests
import time

def check_api_health():
    try:
        response = requests.get(
            'https://api.ndara.ai/health',
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

# Monitor every minute
while True:
    if not check_api_health():
        alert_team("ndara.ai API is down!")
    time.sleep(60)
```

### Metrics to Track

1. **API Performance**:
   - Response time (p50, p95, p99)
   - Success rate
   - Error rate by type
   - Rate limit hits

2. **AI Quality**:
   - Average confidence score
   - Quality score distribution
   - Escalation rate
   - Customer satisfaction

3. **Business Metrics**:
   - Conversations handled
   - Conversion rate
   - Token usage
   - Cost per conversation

### Logging Best Practices

```python
import logging
import json

logger = logging.getLogger('ndara_integration')

def log_api_call(endpoint, request_data, response_data, duration_ms):
    logger.info(json.dumps({
        'event': 'api_call',
        'endpoint': endpoint,
        'duration_ms': duration_ms,
        'success': response_data.get('success'),
        'business_id': request_data.get('business_id'),
        'timestamp': datetime.now().isoformat()
    }))

def log_error(endpoint, error_type, error_message):
    logger.error(json.dumps({
        'event': 'api_error',
        'endpoint': endpoint,
        'error_type': error_type,
        'error_message': error_message,
        'timestamp': datetime.now().isoformat()
    }))
```

---

## SLA and Performance

### Expected Response Times

| Endpoint | p50 | p95 | p99 |
|----------|-----|-----|-----|
| /chat | 1.2s | 2.5s | 4.0s |
| /onboard | 3.0s | 6.0s | 10s |
| /analyze-sales | 2.0s | 4.0s | 7.0s |
| /segment-customers | 1.5s | 3.0s | 5.0s |

### Service Level Agreement

- **Uptime**: 99.9% (8.76 hours downtime/year)
- **Support Response**: <4 hours for critical issues
- **Maintenance Windows**: Sundays 2-4 AM WAT
- **Data Retention**: 12 months minimum

### Rate Limits

| Plan | Requests/Minute | Burst Limit |
|------|-----------------|-------------|
| Starter | 100 | 150 |
| Professional | 1,000 | 1,500 |
| Enterprise | 10,000 | 15,000 |

---

## Migration from Existing System

### Step 1: Parallel Running

Run ndara.ai alongside your current system:

```python
def handle_customer_message(message, customer_id):
    # Get responses from both systems
    old_response = old_system.process(message)
    new_response = ndara_client.chat(message, customer_id)
    
    # Use old system response
    # Log new system response for comparison
    log_comparison(old_response, new_response)
    
    return old_response
```

### Step 2: Gradual Rollout

```python
import random

def handle_customer_message(message, customer_id):
    # 10% traffic to new system
    if random.random() < 0.10:
        return ndara_client.chat(message, customer_id)
    else:
        return old_system.process(message)
```

### Step 3: Full Migration

```python
def handle_customer_message(message, customer_id):
    try:
        # Use ndara.ai
        return ndara_client.chat(message, customer_id)
    except Exception as e:
        # Fallback to old system
        logger.error(f"ndara.ai failed: {e}")
        return old_system.process(message)
```

---

## Support Resources

- **Documentation**: https://docs.ndara.ai
- **API Status**: https://status.ndara.ai
- **Developer Portal**: https://developers.ndara.ai
- **Support Email**: support@ndara.ai
- **Emergency Hotline**: +234-xxx-xxxx (24/7)
- **Slack Community**: #ndara-developers

---

**Version**: 1.0.0  
**Last Updated**: October 10, 2025

