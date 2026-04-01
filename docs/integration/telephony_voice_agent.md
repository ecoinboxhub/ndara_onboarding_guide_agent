# Voice Agent - Telephony Integration Guide (Updated)

## Overview

The Voice Agent is now a **pure AI audio processing service** focused solely on the AI engineering aspects:
- Speech-to-Text (OpenAI Whisper)
- Dialog Management (Customer AI routing)
- Text-to-Speech (ElevenLabs)

**Important**: This service does NOT handle:
- ❌ Actual phone calls (telephony integration is Backend scope)
- ❌ Call routing and telephony infrastructure
- ❌ SMS/Email notifications
- ❌ WhatsApp integration
- ❌ Physical phone number management

These telephony features are **backend infrastructure concerns** handled separately by DevOps/Backend teams.

## New Architecture

```
Voice Agent Service (Port 8003)
├── HTTP API Endpoints
│   ├── /api/v1/onboard         → Onboard business (proxies to Customer AI, same knowledge base)
│   ├── /api/v1/call-summary/{id} → Get call summary (plain text, 24h TTL)
│   ├── /audio/process          → Full pipeline (STT → AI → TTS)
│   ├── /audio/session/start    → Start conversation session (returns greeting text)
│   ├── /audio/greeting         → Get greeting text/audio by call_type and reason
│   ├── /audio/session/end      → End session (generates summary)
│   ├── /voice/test             → Test TTS synthesis
│   ├── /voice/test/info        → TTS config
│   ├── /whisper/test           → Test STT (upload audio, get transcript)
│   └── /whisper/test/info      → STT config
│
├── WebSocket Endpoint
│   └── /audio/stream           → Real-time audio streaming
│
└── Backend integration (code)
    └── StreamBridge            → voice_agent.realtime.StreamBridge (see below)
```

## Integration Points

### For Backend/Telephony Integration

If you need to add telephony capabilities:

1. **Create a separate Telephony Gateway Service** that:
   - Handles telephony provider API (PSTN/SIP/WebRTC)
   - Manages phone calls and call routing
   - Sends audio to Voice Agent via HTTP API or WebSocket
   - Receives synthesized audio back from Voice Agent
   - Handles call transfers, SMS, etc.

2. **Communication Flow:**
```
Phone Call → Telephony Provider → Telephony Gateway → Voice Agent API → AI Services
                                              ↓
Phone Call ← Telephony Provider ← Telephony Gateway ← Synthesized Audio
```

### API Integration Examples

#### Onboard Business (Voice + Chat)
```python
import requests

# Onboard business - same knowledge base for voice and chat
response = requests.post(
    'http://localhost:8003/api/v1/onboard',
    params={'business_id': 'my_business'},
    json={
        "business_info": {"name": "My Business", "phone": "+1234567890", ...},
        "products": [],
        "faqs": [{"question": "...", "answer": "..."}],
        ...
    }
)
result = response.json()  # success, industry, generated_faqs, ai_context
```

#### Shared Memory (Voice + Chat)

Voice and chat share the same Customer AI knowledge base and **conversation memory** when you pass identity:

- **customer_id** – Scopes memory to a customer (same customer sees prior chat history in voice and vice versa)
- **conversation_id** – Scopes memory to a specific conversation thread

Pass these when starting a session or processing audio; they are forwarded to Customer AI.

#### Process Audio via HTTP
```python
import requests

# Send audio to Voice Agent (optional: customer_id, conversation_id, call_type)
with open('recording.mp3', 'rb') as f:
    response = requests.post(
        'http://localhost:8003/audio/process',
        files={'audio_file': f},
        data={
            'business_id': 'beauty_wellness_001',
            'session_id': 'optional-session-id',
            'customer_id': 'cust_123',      # optional - shared memory with chat
            'conversation_id': 'conv_456',  # optional - thread scope
            'call_type': 'inbound'          # inbound | outbound - feature access (appointments, payments)
        }
    )
# Get synthesized audio response
audio_data = response.content
transcript = response.headers.get('X-Transcript')
ai_text = response.headers.get('X-Response-Text')
esc_required = response.headers.get('X-Escalation-Required', 'false').lower() == 'true'
esc_payload = response.headers.get('X-Escalation-Payload')  # JSON if escalation
```

#### WebSocket Protocol

Connect to `ws://host:8003/audio/stream`, then:

1. **Initial setup** – Send JSON first. **`business_name` is required** (provision from onboarding; used in the greeting, not business_id).
   ```json
   {
     "business_id": "beauty_wellness_001",
     "business_name": "Glam Beauty Spa",
     "session_id": "optional-uuid",
     "customer_id": "cust_123",
     "conversation_id": "conv_456",
     "call_type": "inbound",
     "reason": null
   }
   ```
   - `business_name`: **Required.** Display name from onboarding (e.g. from business_info.name / business_profile.business_name).
   - `call_type`: `"inbound"` | `"outbound"` – used for feature access and for the first utterance (greeting).
   - `reason`: For **outbound** only. Examples: `abandoned_cart`, `order_issues`, `technical_fixed`, `promotional`, etc.

2. **Receive** `session_started`:
   ```json
   { "type": "session_started", "session_id": "uuid" }
   ```

3. **Receive** **greeting** (introduction first): one JSON event with text and audio. Play this before capturing/streaming user audio.
   ```json
   { "type": "greeting", "call_type": "outbound", "text": "Good day, this is ... calling about items left in your cart. How can we help you today?", "audio": "<base64 MP3>" }
   ```

4. **Send** raw audio bytes (binary frames). Telephony typically sends 8kHz MULAW mono; the service converts to a Whisper-compatible format.

5. **Receive** events (JSON frames):
   | Type         | Payload                          | Description                    |
   |--------------|----------------------------------|--------------------------------|
   | `greeting`   | `{ "type": "greeting", "call_type", "text", "audio" }` | First utterance (once)        |
   | `transcript` | `{ "type": "transcript", "text": "..." }` | User speech transcribed      |
   | `ai_response`| `{ "type": "ai_response", "text": "..." }` | AI reply text before TTS     |
   | `escalation` | `{ "type": "escalation", "payload": {...} }` | Human handoff requested      |

6. **Receive** audio: binary frames (MP3) for playback.

**StreamBridge (backend integration):** The Voice Agent codebase provides a **StreamBridge** class for backend/telephony integration. It is part of the integration surface—not dead code. Backend teams should take note:

- **What it is:** `voice_agent.realtime.StreamBridge` — a bridge between telephony media streams and the same Voice Agent STT/TTS pipeline. It is not used by the default HTTP/WebSocket server; it is for backend when they need to plug PSTN/SIP (e.g. Twilio Media Streams) into the pipeline with an **event-based protocol** (JSON messages with `event: "media"` and base64 audio, etc.).
- **Where:** `voice_agent/realtime/stream_bridge.py`. Exported from `voice_agent.realtime`.
- **When to use:** (1) Use the **public WebSocket** `ws://host:8003/audio/stream` with the simple protocol above (setup JSON → session_started → greeting → binary frames) from your Telephony Gateway; or (2) if your provider uses structured events (e.g. Twilio Media Streams), integrate using the **StreamBridge** class: call `process_stream(websocket, call_id, business_id, business_name="...", call_type="inbound"|"outbound", reason=...)`. **`business_name` is required** (provision from onboarding); the greeting uses it, not business_id. StreamBridge sends the same call-type– and reason-aware greeting (introduction first).
- **Media proxy:** When connecting PSTN/SIP to the Voice Agent WebSocket, use a stream bridge or media proxy to:
  - Convert telephony audio (MULAW, RTP) to raw bytes for the WebSocket
  - Convert WebSocket MP3 responses back to telephony format (RTP/MULAW) for playback

```javascript
const ws = new WebSocket('ws://localhost:8003/audio/stream');

ws.send(JSON.stringify({
    business_id: 'beauty_wellness_001',
    business_name: 'Glam Beauty Spa',  // required – from onboarding
    session_id: 'optional-uuid',
    customer_id: 'cust_123',
    conversation_id: 'conv_456',
    call_type: 'inbound',
    reason: null  // for outbound: 'abandoned_cart', 'order_issues', 'technical_fixed', 'promotional', etc.
}));

ws.onmessage = (event) => {
    if (typeof event.data === 'string') {
        const msg = JSON.parse(event.data);
        if (msg.type === 'session_started') { /* ... */ }
        else if (msg.type === 'greeting') { playAudioBase64(msg.audio); /* introduction first */ }
        else if (msg.type === 'transcript') { /* msg.text */ }
        else if (msg.type === 'ai_response') { /* msg.text */ }
        else if (msg.type === 'escalation') { /* msg.payload - handoff */ }
    } else {
        playAudio(event.data);  // MP3 bytes
    }
};

ws.send(audioChunkBytes);  // MULAW or PCM chunks
```

#### Session Management

```python
# Start session (business_name required – from onboarding)
resp = requests.post(
    'http://localhost:8003/audio/session/start',
    json={
        "business_id": "beauty_wellness_001",
        "business_name": "Glam Beauty Spa",
        "customer_id": "cust_123",
        "conversation_id": "conv_456",
        "call_type": "inbound"   # inbound | outbound
    }
)
session_id = resp.json()["session_id"]

# Use session_id in /audio/process or WebSocket setup for continuity
```

#### Call Summary

When a session ends (POST `/audio/session/end` or WebSocket disconnect), a natural-language call summary is generated and stored (24h TTL). Backend can fetch and persist:

```python
# End session (returns summary in response)
response = requests.post(
    'http://localhost:8003/audio/session/end',
    params={'session_id': session_id}
)
data = response.json()
summary = data['summary']

# Or fetch later (within 24h)
summary_response = requests.get(
    f'http://localhost:8003/api/v1/call-summary/{session_id}'
)
summary_text = summary_response.text  # text/plain
```

## What Was Removed

The following components were removed as they are backend concerns:

### Removed Directories
- `telephony/` - All telephony integration, call management, briefing system

### Removed Dependencies
- `redis` - Caching (was used for call state)
- `prometheus-client` - Metrics (basic metrics still available)
- `sqlalchemy` - Database (session state now in-memory)

### Removed Configuration
- `TELEPHONY_*` - Telephony provider credentials (Backend-managed)
- `WHATSAPP_*` - WhatsApp integration settings
- `REDIS_URL` - Redis cache settings
- `RECORD_CALLS`, `CALL_RETENTION_DAYS` - Call recording settings

## Testing the Voice Agent

### Using cURL

```bash
# Test TTS
curl -X POST http://localhost:8003/voice/test \
  -H "Content-Type: application/json" \
  -d '{"text": "Good day! How may I help you?", "format": "MP3"}' \
  --output test_voice.mp3

# Test STT (Whisper) — upload audio, get transcript
curl -X POST http://localhost:8003/whisper/test \
  -F "audio_file=@recording.mp3"

# Process audio file (full pipeline)
curl -X POST http://localhost:8003/audio/process \
  -F "audio_file=@recording.mp3" \
  -F "business_id=beauty_wellness_001" \
  --output ai_response.mp3
```

## For Production Telephony Integration

If you need to build a complete voice call system:

1. **Voice Agent Service** (This service - Port 8003)
   - Handles AI audio processing
   - STT, Dialog, TTS pipeline
   
2. **Telephony Gateway Service** (Create separately)
   - Integrates with telephony provider (PSTN, SIP, WebRTC)
   - Manages call state and routing
   - Forwards audio to Voice Agent
   - Handles SMS, call transfers, etc.

3. **Customer AI** (Port 8000)
   - Handles customer conversations

## Migration Notes

If you had a previous telephony-integrated version:

**Before:**
- Voice Agent handled everything (telephony + AI processing)

**Now:**
- Voice Agent handles only AI processing
- Telephony integration is separate (if needed)

**Benefits:**
- Clear separation of concerns
- AI team focuses on AI
- Backend team handles telephony
- Easier testing and development
- Can swap telephony providers easily

## Compliance & Recording

Call recording, consent, and retention are **telephony concerns**. Implement these in your Telephony Gateway Service, not in the Voice Agent.

## Observability

Basic metrics are available at `/metrics` endpoint. For production monitoring:
- Log aggregation (ELK, Datadog, etc.)
- APM tools (New Relic, Datadog APM)
- Custom metrics (Prometheus, CloudWatch)

Implement comprehensive monitoring in your Telephony Gateway.
