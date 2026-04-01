# WhatsApp Business API Integration Guide

## Overview

Integrate ndara.ai Customer AI with WhatsApp Business API to provide intelligent customer service on WhatsApp. This guide covers complete integration from setup to production.

**Integration Pattern**: WhatsApp → Backend Webhook → Customer AI API → Response → WhatsApp

---

## Prerequisites

### 1. WhatsApp Business API Access
- WhatsApp Business API account
- Phone number verified with WhatsApp
- Business profile approved
- API credentials (Phone Number ID, WhatsApp Business Account ID)

### 2. ndara.ai Setup
- Customer AI API key
- Business onboarded via `/api/v1/onboard`
- Business ID available

### 3. Backend Requirements
- Public HTTPS endpoint for webhooks
- SSL certificate (required by WhatsApp)
- Server capable of handling concurrent requests

---

## Architecture

```
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│   WhatsApp   │          │   Backend    │          │ Customer AI  │
│   Customer   │          │   Webhook    │          │     API      │
└──────────────┘          └──────────────┘          └──────────────┘
       │                         │                          │
       │  1. Sends message       │                          │
       │─────────────────────────>│                          │
       │                         │                          │
       │                         │  2. POST /api/v1/chat    │
       │                         │─────────────────────────>│
       │                         │                          │
       │                         │  3. AI processes         │
       │                         │     (RAG + Intent        │
       │                         │      + Sentiment)        │
       │                         │                          │
       │                         │  4. Returns response     │
       │                         │<─────────────────────────│
       │                         │                          │
       │  5. Sends AI response   │                          │
       │<─────────────────────────│                          │
       │                         │                          │
       │                         │  6. Stores conversation  │
       │                         │     & handles actions    │
```

---

## Setup Steps

### Step 1: Configure WhatsApp Business API

1. **Register webhook URL:**
```bash
# Your webhook endpoint
WEBHOOK_URL="https://yourdomain.com/webhooks/whatsapp"
VERIFY_TOKEN="your_random_verification_token"
```

2. **Subscribe to message events:**
```bash
curl -X POST \
  "https://graph.facebook.com/v18.0/{phone-number-id}/subscribed_apps" \
  -H "Authorization: Bearer {access-token}" \
  -d "subscribed_fields=messages"
```

### Step 2: Implement Webhook Endpoint

#### Node.js/Express Example

```javascript
const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());

// Webhook verification (GET request from WhatsApp)
app.get('/webhooks/whatsapp', (req, res) => {
  const mode = req.query['hub.mode'];
  const token = req.query['hub.verify_token'];
  const challenge = req.query['hub.challenge'];
  
  if (mode === 'subscribe' && token === process.env.VERIFY_TOKEN) {
    console.log('Webhook verified');
    res.status(200).send(challenge);
  } else {
    res.sendStatus(403);
  }
});

// Webhook receiver (POST request from WhatsApp)
app.post('/webhooks/whatsapp', async (req, res) => {
  try {
    const body = req.body;
    
    // Respond immediately to WhatsApp (required within 20 seconds)
    res.sendStatus(200);
    
    // Process message asynchronously
    if (body.object === 'whatsapp_business_account') {
      for (const entry of body.entry) {
        for (const change of entry.changes) {
          if (change.field === 'messages') {
            await handleIncomingMessage(change.value);
          }
        }
      }
    }
  } catch (error) {
    console.error('Webhook error:', error);
    res.sendStatus(500);
  }
});

async function handleIncomingMessage(value) {
  const messages = value.messages;
  if (!messages || messages.length === 0) return;
  
  const message = messages[0];
  const from = message.from; // Customer phone number
  const messageText = message.text?.body;
  const messageId = message.id;
  
  if (!messageText) return; // Skip non-text messages for now
  
  // Extract business context (from phone number or routing)
  const businessId = getBusinessIdFromPhoneNumber(value.metadata.phone_number_id);
  
  // Call ndara.ai Customer AI
  const aiResponse = await callNdaraAI(businessId, messageText, from);
  
  // Send response back to WhatsApp
  await sendWhatsAppMessage(
    value.metadata.phone_number_id,
    from,
    aiResponse.response
  );
  
  // Handle special actions
  if (aiResponse.escalation_required) {
    await notifyBusinessOwner(businessId, from, aiResponse);
  }
  
  if (aiResponse.intent?.type === 'appointment_booking') {
    await handleAppointmentBooking(businessId, from, aiResponse.intent.entities);
  }
}

async function callNdaraAI(businessId, message, customerId) {
  const response = await axios.post(
    `${process.env.NDARA_API_URL}/api/v1/chat`,
    {
      message: message,
      customer_id: customerId,
      context: {
        channel: 'whatsapp',
        platform: 'whatsapp_business_api'
      }
    },
    {
      headers: {
        'X-API-Key': process.env.NDARA_API_KEY
      },
      params: {
        business_id: businessId
      }
    }
  );
  
  return response.data;
}

async function sendWhatsAppMessage(phoneNumberId, to, text) {
  await axios.post(
    `https://graph.facebook.com/v18.0/${phoneNumberId}/messages`,
    {
      messaging_product: 'whatsapp',
      to: to,
      type: 'text',
      text: { body: text }
    },
    {
      headers: {
        'Authorization': `Bearer ${process.env.WHATSAPP_ACCESS_TOKEN}`,
        'Content-Type': 'application/json'
      }
    }
  );
}

app.listen(3000, () => console.log('Webhook server running on port 3000'));
```

#### Python/Flask Example

```python
from flask import Flask, request, jsonify
import requests
import os
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
NDARA_API_KEY = os.getenv('NDARA_API_KEY')
NDARA_API_URL = os.getenv('NDARA_API_URL', 'http://localhost:8000')

@app.route('/webhooks/whatsapp', methods=['GET'])
def verify_webhook():
    """Webhook verification endpoint"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        logger.info('Webhook verified')
        return challenge, 200
    else:
        return 'Forbidden', 403

@app.route('/webhooks/whatsapp', methods=['POST'])
def webhook():
    """Webhook receiver for WhatsApp messages"""
    try:
        body = request.get_json()
        
        # Process messages
        if body.get('object') == 'whatsapp_business_account':
            for entry in body.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        handle_message(change['value'])
        
        return '', 200
    
    except Exception as e:
        logger.error(f'Webhook error: {e}')
        return '', 500

def handle_message(value):
    """Process incoming WhatsApp message"""
    messages = value.get('messages', [])
    if not messages:
        return
    
    message = messages[0]
    customer_number = message['from']
    message_text = message.get('text', {}).get('body')
    
    if not message_text:
        return
    
    # Get business context
    phone_number_id = value['metadata']['phone_number_id']
    business_id = get_business_id_from_phone(phone_number_id)
    
    # Call Customer AI
    ai_response = call_customer_ai(business_id, message_text, customer_number)
    
    # Send response
    send_whatsapp_message(phone_number_id, customer_number, ai_response['response'])
    
    # Handle special cases
    if ai_response.get('escalation_required'):
        notify_business_owner(business_id, customer_number, ai_response)
    
    if ai_response.get('intent', {}).get('type') == 'appointment_booking':
        handle_booking_intent(business_id, customer_number, ai_response['intent'])

def call_customer_ai(business_id, message, customer_id):
    """Call ndara.ai Customer AI API"""
    response = requests.post(
        f'{NDARA_API_URL}/api/v1/chat',
        params={'business_id': business_id},
        headers={'X-API-Key': NDARA_API_KEY},
        json={
            'message': message,
            'customer_id': customer_id,
            'context': {'channel': 'whatsapp'}
        },
        timeout=30
    )
    
    return response.json()

def send_whatsapp_message(phone_number_id, to, text):
    """Send message via WhatsApp Business API"""
    url = f'https://graph.facebook.com/v18.0/{phone_number_id}/messages'
    
    requests.post(
        url,
        headers={
            'Authorization': f'Bearer {WHATSAPP_TOKEN}',
            'Content-Type': 'application/json'
        },
        json={
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'text',
            'text': {'body': text}
        }
    )

if __name__ == '__main__':
    app.run(port=3000)
```

---

## Message Flow Details

### 1. Incoming Message Processing

**WhatsApp Webhook Payload:**
```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "234XXXXXXXXX",
              "phone_number_id": "PHONE_NUMBER_ID"
            },
            "contacts": [
              {
                "profile": {"name": "John Doe"},
                "wa_id": "234XXXXXXXXX"
              }
            ],
            "messages": [
              {
                "from": "234XXXXXXXXX",
                "id": "wamid.xxx",
                "timestamp": "1696953600",
                "text": {"body": "Hello, I need help"},
                "type": "text"
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

### 2. AI Processing

Call Customer AI API:
```javascript
const aiResponse = await axios.post(
  `${NDARA_API_URL}/api/v1/chat`,
  {
    message: "Hello, I need help",
    customer_id: "234XXXXXXXXX",
    context: {
      channel: "whatsapp",
      customer_name: "John Doe"
    }
  },
  {
    params: { business_id: "biz_12345" },
    headers: { 'X-API-Key': API_KEY }
  }
);

// aiResponse.data contains:
// - response: "Hello! I'm here to help..."
// - intent: { type: "general_inquiry", confidence: 0.85 }
// - sentiment: { sentiment: "neutral", score: 0.05 }
// - escalation_required: false
// - quality_score: 0.87
```

### 3. Response Delivery

**Send to WhatsApp:**
```javascript
await axios.post(
  `https://graph.facebook.com/v18.0/${phoneNumberId}/messages`,
  {
    messaging_product: 'whatsapp',
    to: customerPhoneNumber,
    type: 'text',
    text: {
      body: aiResponse.response
    }
  },
  {
    headers: {
      'Authorization': `Bearer ${WHATSAPP_TOKEN}`
    }
  }
);
```

---

## Advanced Features

### Handling Media Messages

```javascript
// Image message from customer
if (message.type === 'image') {
  const imageId = message.image.id;
  
  // Download image
  const imageUrl = await getMediaUrl(imageId);
  
  // For now, respond asking for text description
  await sendWhatsAppMessage(
    phoneNumberId,
    from,
    "I can see you've sent an image. Could you please describe what you need help with?"
  );
  
  // TODO: Implement image analysis with Vision API
}
```

### Handling Quick Reply Buttons

```javascript
// Send message with quick reply buttons
async function sendMessageWithButtons(phoneNumberId, to, text, buttons) {
  await axios.post(
    `https://graph.facebook.com/v18.0/${phoneNumberId}/messages`,
    {
      messaging_product: 'whatsapp',
      to: to,
      type: 'interactive',
      interactive: {
        type: 'button',
        body: { text: text },
        action: {
          buttons: buttons.map((btn, idx) => ({
            type: 'reply',
            reply: {
              id: `btn_${idx}`,
              title: btn
            }
          }))
        }
      }
    },
    {
      headers: {
        'Authorization': `Bearer ${WHATSAPP_TOKEN}`
      }
    }
  );
}

// Usage based on AI intent
if (aiResponse.intent.type === 'appointment_booking') {
  await sendMessageWithButtons(
    phoneNumberId,
    from,
    aiResponse.response,
    ['Book Now', 'View Schedule', 'Call Us']
  );
}
```

### Session Management

```javascript
const sessions = new Map(); // In-memory (use Redis for production)

function getOrCreateSession(customerId, businessId) {
  const key = `${businessId}:${customerId}`;
  
  if (!sessions.has(key)) {
    sessions.set(key, {
      conversation_id: generateUUID(),
      created_at: Date.now(),
      message_count: 0,
      context: {}
    });
  }
  
  return sessions.get(key);
}

// Use in message handler
const session = getOrCreateSession(from, businessId);
session.message_count++;

// Include in AI call
const aiResponse = await callNdaraAI(businessId, messageText, from, {
  conversation_id: session.conversation_id,
  message_count: session.message_count
});

// Clean up old sessions (24 hours)
setInterval(() => {
  const now = Date.now();
  for (const [key, session] of sessions.entries()) {
    if (now - session.created_at > 24 * 60 * 60 * 1000) {
      sessions.delete(key);
    }
  }
}, 60 * 60 * 1000); // Every hour
```

---

## Best Practices

### 1. Rate Limiting

WhatsApp Business API limits:
- **80 messages/second** per phone number
- **1000 messages/day** for new businesses
- **Unlimited** for established businesses

**Implementation:**
```javascript
const rateLimit = require('express-rate-limit');

const limiter = rateLimit({
  windowMs: 1000, // 1 second
  max: 70, // 70 requests per second (buffer below 80 limit)
  message: 'Too many messages, please try again later'
});

app.post('/webhooks/whatsapp', limiter, webhook);
```

### 2. Message Templating

WhatsApp requires template approval for business-initiated messages:

```javascript
// Within 24-hour window: Free-form text allowed
// Outside 24-hour window: Use approved templates only

function canSendFreeform(lastCustomerMessage) {
  const hoursSinceLastMessage = (Date.now() - lastCustomerMessage) / (1000 * 60 * 60);
  return hoursSinceLastMessage < 24;
}

async function sendMessage(phoneNumberId, to, text, lastCustomerMessageTime) {
  if (canSendFreeform(lastCustomerMessageTime)) {
    // Send free-form text
    await sendWhatsAppMessage(phoneNumberId, to, text);
  } else {
    // Use approved template
    await sendTemplate(phoneNumberId, to, 'approved_template_name', [text]);
  }
}
```

### 3. Error Recovery

```javascript
async function sendMessageWithRetry(phoneNumberId, to, text, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      await sendWhatsAppMessage(phoneNumberId, to, text);
      return true;
    } catch (error) {
      logger.error(`Attempt ${attempt + 1} failed:`, error);
      
      if (attempt < maxRetries - 1) {
        // Exponential backoff
        await sleep(Math.pow(2, attempt) * 1000);
      }
    }
  }
  
  // All retries failed - log to database for manual follow-up
  await logFailedMessage(businessId, to, text);
  return false;
}
```

### 4. Handling Escalations

```javascript
async function handleIncomingMessage(value) {
  // ... process message ...
  
  const aiResponse = await callNdaraAI(businessId, messageText, from);
  
  // Check for escalation
  if (aiResponse.escalation_required) {
    // Notify business owner immediately
    await notifyBusinessOwner({
      businessId: businessId,
      customerId: from,
      severity: aiResponse.severity,
      contextSummary: aiResponse.context_summary,
      conversationUrl: `https://dashboard.ndara.ai/conversations/${session.conversation_id}`
    });
    
    // Send acknowledgment to customer
    await sendWhatsAppMessage(
      phoneNumberId,
      from,
      "A team member will reach out to you shortly to address your concern. We appreciate your patience."
    );
  } else {
    // Send AI response
    await sendWhatsAppMessage(phoneNumberId, from, aiResponse.response);
  }
}

async function notifyBusinessOwner(escalation) {
  // Send via multiple channels
  await Promise.all([
    sendEmail(escalation),
    sendPushNotification(escalation),
    sendSMS(escalation) // For critical severity
  ]);
  
  // Log in database
  await logEscalation(escalation);
}
```

---

## Production Deployment

### SSL Certificate

WhatsApp requires HTTPS:

```bash
# Using Let's Encrypt
sudo certbot --nginx -d yourdomain.com
```

### Scalability

**Load Balancing:**
```nginx
upstream webhook_servers {
    server webhook1:3000;
    server webhook2:3000;
    server webhook3:3000;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    location /webhooks/whatsapp {
        proxy_pass http://webhook_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Horizontal Scaling:**
- Deploy multiple webhook servers
- Use Redis for session storage
- Queue messages for processing (RabbitMQ/SQS)

### Monitoring

```javascript
// Track metrics
const metrics = {
  messagesReceived: 0,
  messagesProcessed: 0,
  messagesFailed: 0,
  avgResponseTime: 0,
  escalations: 0
};

// Prometheus metrics endpoint
app.get('/metrics', (req, res) => {
  res.send(`
# HELP whatsapp_messages_received Total messages received from WhatsApp
# TYPE whatsapp_messages_received counter
whatsapp_messages_received ${metrics.messagesReceived}

# HELP whatsapp_messages_processed Total messages successfully processed
# TYPE whatsapp_messages_processed counter
whatsapp_messages_processed ${metrics.messagesProcessed}

# HELP whatsapp_escalations Total escalations to business owner
# TYPE whatsapp_escalations counter
whatsapp_escalations ${metrics.escalations}
  `);
});
```

---

## Testing

### WhatsApp Sandbox

Use WhatsApp Cloud API test number:

```bash
# Test phone number (sandbox)
TEST_NUMBER="+1 555 025 3121"

# Send test message
curl -X POST "https://graph.facebook.com/v18.0/PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "'$TEST_NUMBER'",
    "type": "text",
    "text": {"body": "Test message"}
  }'
```

### Integration Testing

```javascript
// Test complete flow
describe('WhatsApp Integration', () => {
  it('should process message and respond', async () => {
    // Mock WhatsApp webhook payload
    const webhookPayload = createMockWebhookPayload('Hello');
    
    // Send to webhook endpoint
    const response = await request(app)
      .post('/webhooks/whatsapp')
      .send(webhookPayload);
    
    expect(response.status).toBe(200);
    
    // Verify AI was called
    expect(mockNdaraAI).toHaveBeenCalledWith(
      expect.objectContaining({
        message: 'Hello'
      })
    );
    
    // Verify WhatsApp response sent
    expect(mockWhatsAppSend).toHaveBeenCalled();
  });
});
```

---

## Troubleshooting

### Common Issues

**1. Webhook not receiving messages**
- Check webhook URL is HTTPS
- Verify webhook subscription is active
- Check firewall/security group settings
- Ensure SSL certificate is valid

**2. Messages not being sent**
- Verify WhatsApp access token is valid
- Check phone number ID is correct
- Ensure business account is approved
- Check rate limits not exceeded

**3. Slow responses**
- Add async processing with queues
- Implement caching for business data
- Use connection pooling
- Optimize database queries

**4. Session management issues**
- Use Redis instead of in-memory storage
- Implement session cleanup
- Handle session expiry gracefully

---

## Checklist

Before going live:

- [ ] Webhook endpoint deployed with HTTPS
- [ ] SSL certificate valid and configured
- [ ] WhatsApp Business API account approved
- [ ] Webhook verified and subscribed to messages
- [ ] ndara.ai API key configured
- [ ] All businesses onboarded
- [ ] Error handling implemented
- [ ] Retry logic configured
- [ ] Rate limiting implemented
- [ ] Session management tested
- [ ] Escalation flow tested
- [ ] Monitoring and logging configured
- [ ] Load testing completed
- [ ] Fallback responses configured
- [ ] Support team notified and trained

---

## Support

**WhatsApp API Issues**: Meta Support  
**ndara.ai API Issues**: support@ndara.ai  
**Integration Help**: Slack #whatsapp-integration

---

**Version**: 1.0.0  
**Last Updated**: October 10, 2025  
**WhatsApp API Version**: v18.0

