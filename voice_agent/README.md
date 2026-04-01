# Voice Agent - AI Audio Processing Service

## Overview

The Voice Agent is a pure AI audio processing service that handles speech-to-text, intelligent dialog management, and text-to-speech. It acts as the voice interface for businesses, processing audio through OpenAI Whisper (STT), routing to Customer AI for responses, and synthesizing natural-sounding Nigerian English speech via ElevenLabs (TTS).

**Note**: This is the AI processing service only. It does not handle telephony infrastructure, call routing, or actual phone calls. Those are backend integration concerns handled separately.

## Core Features

✅ **Speech-to-Text** - OpenAI Whisper for accurate transcription  
✅ **AI Dialog** - Routes to Customer AI  
✅ **Text-to-Speech** - ElevenLabs Nigerian English female voice  
✅ **Session Management** - Maintains conversation context  
✅ **Real-time Audio Streaming** - WebSocket support

## Architecture

```
                                    Voice Agent Service
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│  Audio Input (File/Stream)                                               │
│         ↓                                                                 │
│  ┌──────────────────┐                                                    │
│  │ OpenAI Whisper   │ ← Speech-to-Text                                  │
│  │ (STT)            │                                                     │
│  └────────┬─────────┘                                                    │
│           ↓                                                               │
│  ┌──────────────────┐       ┌─────────────────────┐                     │
│  │ Agent Router     │  ───→ │ Customer AI         │ Port 8000          │
│  │ (Dialog Mgmt)    │       │ (Conversations)     │                     │
│  └────────┬─────────┘       └─────────────────────┘                     │
│           ↓                                                               │
│  ┌──────────────────┐                                                    │
│  │ Prompt Processor │ ← Nigerian English Tone                           │
│  └────────┬─────────┘                                                    │
│           ↓                                                               │
│  ┌──────────────────┐                                                    │
│  │ ElevenLabs TTS   │ ← Text-to-Speech                                  │
│  └────────┬─────────┘                                                    │
│           ↓                                                               │
│  Audio Output (Synthesized)                                              │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
                              Port 8003
```

## Quick Start

### 1. Install Dependencies

```bash
cd voice_agent
pip install --upgrade pip   # See repo SECURITY.md (pip tar/symlink fix)
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the `.env.example` to `.env` and configure:

```env
# OpenAI (for Whisper STT)
OPENAI_API_KEY=sk-...your_key_here...

# ElevenLabs (for TTS)
ELEVENLABS_API_KEY=...your_key_here...
ELEVENLABS_VOICE_ID=...your_voice_id...

# Customer AI Integration
CUSTOMER_AI_BASE_URL=http://localhost:8000
CUSTOMER_AI_API_KEY=dev-key-12345
```

### 3. Start the Service

From the `voice_agent` directory:

```bash
python main.py
```

The service will start on `http://localhost:8003`.

**If you run from the project root** (e.g. when `voice_agent` is a package), use:

```bash
# From repo root
export PYTHONPATH="$(pwd)"   # or set PYTHONPATH to the repo root
cd voice_agent && python -m voice_agent.main
```

On Windows (PowerShell): `$env:PYTHONPATH = "C:\path\to\AI-PROJECT-2"; cd voice_agent; python -m voice_agent.main`

## API Endpoints

### Onboarding

#### `POST /api/v1/onboard`
Onboard a business for voice and chat. Proxies to Customer AI - same knowledge base powers both channels.

**Request:**
```bash
curl -X POST "http://localhost:8003/api/v1/onboard?business_id=my_business" \
  -H "Content-Type: application/json" \
  -d '{"business_info": {"name": "My Business", ...}, "products": [], "faqs": []}'
```

Supports same formats as Customer AI: `business_id` as query param with KnowledgeData in body, or legacy format with `business_id` and `business_data` in body.

**Response:** Same as Customer AI (success, industry, generated_faqs, ai_context, etc.)

### Audio Processing

#### `POST /audio/process`
Process audio file through the full pipeline (STT → AI → TTS)

**Request (optional customer_id, conversation_id for shared memory with chat):**
```bash
curl -X POST http://localhost:8003/audio/process \
  -F "audio_file=@recording.mp3" \
  -F "business_id=beauty_wellness_001" \
  -F "customer_id=cust_123" \
  -F "conversation_id=conv_456"
```

**Response:**
- Audio file (MP3)
- Headers:
  - `X-Transcript`: User's transcribed speech
  - `X-Response-Text`: AI's text response

#### Introduction first (inbound vs outbound)
For every call, the agent’s **first utterance (greeting)** is played before any user audio. The greeting uses the **business name** provisioned from onboarding (e.g. from `business_info.name` or `business_profile.business_name`)—**not** `business_id`. Inbound and outbound use different templates:
- **Inbound:** *"Good day, you've reached [Business Name]. How may I help you today?"*
- **Outbound:** *"Good day, this is [Business Name] calling [about reason]. How can we help you today?"* — optional `reason` customizes the line.

#### `POST /audio/session/start`
Start a new conversation session. **`business_name` is required** (provision from onboarding); it is used in the greeting. Pass `customer_id` and `conversation_id` to share memory with chat. Use `call_type` and optional `reason` (for outbound).

**Request:**
```json
{
  "business_id": "beauty_wellness_001",
  "business_name": "Glam Beauty Spa",
  "customer_id": "optional_customer_id",
  "conversation_id": "optional_conversation_id",
  "call_type": "inbound",
  "reason": null
}
```
- `business_name`: **Required.** Display name from onboarding (do not use business_id).
- `call_type`: `"inbound"` | `"outbound"`
- `reason`: For outbound only. Examples: `abandoned_cart`, `order_issues`, `technical_fixed`, `promotional`, etc.

**Response:**
```json
{
  "session_id": "uuid-here",
  "status": "active",
  "business_id": "beauty_wellness_001",
  "greeting": {
    "call_type": "inbound",
    "text": "Good day, you've reached Glam Beauty Spa. How may I help you today?"
  }
}
```

#### `GET /audio/greeting`
Get the first-utterance (greeting) text and optionally synthesized audio. **`business_name` is required** (query param; provision from onboarding). Params: `business_name` (required), `call_type` (default `inbound`), `reason` (optional, for outbound), `include_audio` (default `false`).

**Response (without audio):** `{ "call_type": "inbound", "text": "..." }`  
**With `include_audio=true`:** adds `"audio_base64": "..."` (MP3).

#### `POST /audio/session/end`
End a conversation session. Generates a natural-language call summary (also stored for 24h; fetch via `GET /api/v1/call-summary/{session_id}`).

**Query Parameter:** `session_id`

**Response:**
```json
{
  "session_id": "uuid-here",
  "status": "ended",
  "turn_count": 5,
  "duration_seconds": 180,
  "conversation_history": [...],
  "summary": "Customer inquired about..."
}
```

#### `GET /api/v1/call-summary/{session_id}`
Get call summary as plain text. Summaries are generated on session end; stored in-memory with 24h TTL. Backend should fetch and persist as needed.

**Response:** `text/plain` body with natural-language summary

#### `GET /audio/session/{session_id}`
Get session status and history

**Response:**
```json
{
  "session_id": "uuid-here",
  "business_id": "beauty_wellness_001",
  "turn_count": 3,
  "conversation_history": [...]
}
```

#### `WebSocket /audio/stream`
Real-time audio streaming. **`business_name` is required** in the setup message (provision from onboarding). **Introduction first:** after `session_started`, the server sends a **greeting** event (text + audio); play that before streaming user audio.

**Setup Message:**
```json
{
  "business_id": "beauty_wellness_001",
  "business_name": "Glam Beauty Spa",
  "session_id": "optional-uuid",
  "customer_id": "optional-for-shared-memory",
  "conversation_id": "optional-for-shared-memory",
  "call_type": "inbound",
  "reason": null
}
```
- `business_name`: **Required.** Display name from onboarding (do not use business_id).
- `call_type`: `"inbound"` | `"outbound"`
- `reason`: For outbound (e.g. `abandoned_cart`, `order_issues`, `technical_fixed`, `promotional`).

**After setup:** Server sends `session_started`, then a **greeting** event: `{ "type": "greeting", "call_type": "...", "text": "...", "audio": "<base64 MP3>" }`. Play the greeting audio, then send user audio bytes. If `business_name` is missing, the server sends `{ "type": "error", "detail": "..." }` and closes.

**Stream Audio:** Send audio bytes, receive:
- JSON: `transcript`, `ai_response`, `escalation`, or (once) `greeting`
- Binary: MP3 synthesized speech

### Voice Testing (TTS)

#### `POST /voice/test`
Test voice synthesis (TTS only).

**Request:**
```json
{
  "text": "Good day! How may I help you today?",
  "format": "MP3"
}
```

**Response:** Audio file (MP3/WAV)

#### `GET /voice/test/info`
Get voice configuration details (ElevenLabs voice ID, provider, sample rate).

**Response:** JSON with `status`, `current_voice`, `audio_settings`.

### Whisper Testing (STT)

#### `POST /whisper/test`
Test speech-to-text. Upload an audio file (MP3, WAV, WebM); get back the transcribed text. Use this to verify the STT pipeline before testing the full voice flow.

**Request:** `multipart/form-data` with `audio_file` (required). Max file size 25 MB.

**Response:**
```json
{
  "status": "success",
  "transcript": "Transcribed text here...",
  "filename": "recording.mp3",
  "size_bytes": 12345
}
```

#### `GET /whisper/test/info`
Get Whisper STT configuration (provider, model, supported input formats).

**Response:** JSON with `status`, `stt` (provider, model, sample_rate, supported_input_formats).

### Utility Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `GET /metrics` - Basic metrics (if enabled)

## Voice Configuration

### Nigerian English Voice

The service uses a custom ElevenLabs voice configured for Nigerian English:

**Voice Characteristics:**
- Gender: Female
- Accent: Nigerian English
- Tone: Professional, warm, conversational
- Provider: ElevenLabs

**Response Processing:**
- Brevity enforcement (progressive disclosure)
- Nigerian English tone and phrasing
- Micro-confirmations for critical details (time, money, location)
- Natural conversation patterns

## Audio Settings

### Supported Formats

**Input:**
- MP3, WAV, WEBM
- Sample Rates: 8kHz, 16kHz, 44.1kHz
- Channels: Mono or Stereo

**Output:**
- MP3 (default)
- WAV (LINEAR16)
- Sample Rate: 16kHz
- Channels: Mono

### Processing Pipeline

1. **Input Audio** → Convert to Whisper-compatible format
2. **Whisper STT** → Transcribe to text
3. **Agent Router** → Route to Customer AI
4. **Prompt Processor** → Apply Nigerian English tone
5. **ElevenLabs TTS** → Synthesize speech
6. **Output Audio** → Return in requested format

## Integration with Other Services

### Customer AI (Port 8000)

The Voice Agent integrates with Customer AI for handling:
- Customer inquiries
- Service requests
- Product information
- Feature access (appointments, orders, payments)

**Context Sent:**
```json
{
  "channel": "voice",
  "session_id": "uuid",
  "business_id": "business_id",
  "customer_id": "optional - scopes memory for shared voice/chat",
  "conversation_id": "optional - scopes memory to thread"
}
```

When `customer_id` or `conversation_id` is provided, Customer AI uses the same ConversationManager scope as chat, so prior chat history is available in voice and vice versa.

## Development

### Project Structure

```
voice_agent/
├── realtime/
│   ├── stt_whisper.py          # OpenAI Whisper STT
│   ├── tts_elevenlabs.py       # ElevenLabs TTS
│   └── stream_bridge.py        # StreamBridge for backend/telephony integration (see below)
├── dialog/
│   ├── agent_router.py         # AI routing logic
│   └── prompt_processor.py     # Nigerian English processing
├── analytics/
│   └── quality_metrics.py      # Basic metrics
├── app.py                      # FastAPI app
├── config.py                   # Configuration
├── main.py                     # Entry point
├── requirements.txt            # Dependencies
└── tests/                      # Automated tests (pytest)
```

### StreamBridge (Backend / Telephony Integration)

The **StreamBridge** class (`voice_agent.realtime.StreamBridge`) is provided for **backend and telephony integration**. It is not used by the default HTTP/WebSocket server; it is a reusable component the backend team can use to connect PSTN/SIP media streams to the same Voice Agent STT/TTS pipeline.

- **Purpose:** Bridge between telephony media streams (e.g. Twilio, SIP) and the voice processing pipeline. Backend’s Telephony Gateway can instantiate `StreamBridge(config)`, pass a WebSocket (or equivalent), and use `process_stream(websocket, call_id, business_id, ...)` to run STT → Customer AI → TTS on incoming audio.
- **Location:** `voice_agent/realtime/stream_bridge.py`. Exported as `StreamBridge` from `voice_agent.realtime`.
- **Protocol:** StreamBridge expects structured JSON messages (e.g. `event: "media"` with base64 audio). The public WebSocket endpoint `POST /audio/stream` uses a simpler protocol (one setup JSON message, then raw binary audio frames). Backend should either use the Voice Agent’s `/audio/stream` WebSocket as documented in `docs/integration/telephony_voice_agent.md`, or integrate using the StreamBridge class if they need the event-based protocol (e.g. for Twilio Media Streams).
- **Documentation:** See [Telephony Integration Guide](../docs/integration/telephony_voice_agent.md) for the StreamBridge / media proxy section and backend responsibilities.

This avoids dead code: StreamBridge is intentionally part of the integration surface for backend/telephony.

### Running Tests

From the **project root** (so `voice_agent` is importable):

```bash
# Install test dependencies (in voice_agent or repo venv)
pip install pytest pytest-asyncio httpx

# Run Voice Agent tests
pytest voice_agent/tests/ -v
```

From inside `voice_agent` with the parent on `PYTHONPATH`:

```bash
cd voice_agent
pytest tests/ -v
```

## Performance

**Target Metrics:**
- STT Latency: < 1 second
- AI Response: < 1 second
- TTS Synthesis: < 1 second
- **Total Turn Latency: < 2 seconds**

## Troubleshooting

### "Could not access microphone"
- Grant microphone permissions in your browser
- Use HTTPS or localhost (required for WebRTC)

### "Failed to transcribe audio"
- Check OpenAI API key is valid
- Ensure audio file is not corrupted
- Verify audio format is supported

### "Failed to synthesize speech"
- Check ElevenLabs API key and voice ID
- Verify account has credits
- Check character limits

### "Customer AI not connected"
- Ensure Customer AI is running on port 8000
- Check `CUSTOMER_AI_BASE_URL` in config
- Verify API key matches

## Production Deployment

For production deployment:

1. Set appropriate `HOST` and `PORT` in config
2. Use production-grade server (e.g., Gunicorn)
3. Set up SSL/TLS for HTTPS
4. Configure rate limiting
5. Enable monitoring and logging
6. Scale horizontally as needed

## License

Internal use only - Part of AI-PROJECT-2

## Support

For issues or questions, refer to the main project documentation in `/docs`.