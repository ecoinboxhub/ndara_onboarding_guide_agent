# Voice Agent – Ready for DevOps / Backend Testing

## Status: READY

The Voice Agent is a **pure AI audio processing service** (no telephony). It is ready for DevOps deployment and backend integration testing.

---

## What the Voice Agent Provides

- **Port:** 8003 (configurable via `PORT` in .env)
- **Architecture:** Audio In → Whisper STT → Agent Router → **Customer AI** (external) → ElevenLabs TTS → Audio Out
- **Docs:** [Telephony / Voice Integration](https://github.com/ndaraAI-project/AI-PROJECT/blob/main/docs/integration/telephony_voice_agent.md) (integration guide for backend)

### Main endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check (STT, TTS, Customer AI configured) |
| `/voice/test` | POST | TTS only (JSON: `{"text":"...", "format":"MP3"}`) |
| `/voice/test/info` | GET | TTS config (voice ID, provider) |
| `/whisper/test` | POST | STT test: upload audio file, get transcript (multipart: `audio_file`) |
| `/whisper/test/info` | GET | STT config (provider, model, formats) |
| `/audio/session/start` | POST | Start session (returns greeting); **business_name** required (from onboarding); call_type, reason for outbound |
| `/audio/greeting` | GET | Get greeting text/audio; **business_name** required (query param); call_type, optional reason |
| `/audio/session/end` | POST | End session, get summary |
| `/api/v1/call-summary/{session_id}` | GET | Get call summary (plain text, 24h TTL) |
| `/audio/process` | POST | Full pipeline: STT → Customer AI → TTS (multipart: `audio_file`, `business_id`, etc.) |
| `/audio/stream` | WebSocket | Real-time audio streaming |
| `/api/v1/onboard` | POST | Onboard business (proxies to Customer AI) |

---

## Environment Variables (Voice Agent `.env`)

### Required

- `OPENAI_API_KEY` – Whisper STT
- `ELEVENLABS_API_KEY` – TTS
- `ELEVENLABS_VOICE_ID` – TTS voice (e.g. Nigerian English)

### Customer AI (dev/staging)

To point the Voice Agent at the **dev Customer AI** instance:

```env
# Use the API base URL only (no /docs path)
CUSTOMER_AI_BASE_URL=https://dev.compute.ndara.ai
CUSTOMER_AI_API_KEY=<key provided by DevOps for dev.compute.ndara.ai>
```

- **Base URL:** `https://dev.compute.ndara.ai` (no trailing slash, no `/docs`)
- **API key:** DevOps/backend should provide the key that `dev.compute.ndara.ai` expects (e.g. `X-API-Key`).

---

## Checklist for DevOps / Backend

- [ ] Deploy Voice Agent with required env vars (OpenAI, ElevenLabs, Customer AI URL and key).
- [ ] Ensure Voice Agent can reach `CUSTOMER_AI_BASE_URL` (e.g. `https://dev.compute.ndara.ai`) and that the API key is valid.
- [ ] Verify `GET /health` returns 200 and `customer_ai` is reported as configured/reachable.
- [ ] Test `POST /voice/test` (TTS only).
- [ ] Test `POST /whisper/test` (STT only): upload an MP3/WAV, verify transcript in response.
- [ ] Test full pipeline: `POST /audio/process` with an audio file and `business_id` (business must be onboarded on Customer AI first, via Voice Agent `/api/v1/onboard` or directly on Customer AI).
- [ ] Optional: test WebSocket `/audio/stream` for real-time flows (after setup, play greeting then stream user audio).
- [ ] **Introduction first:** For every call, the agent plays a greeting before user audio. The greeting uses **business_name** (provisioned from onboarding), not business_id. Inbound vs outbound; for outbound, optional `reason` (e.g. `abandoned_cart`, `order_issues`, `technical_fixed`, `promotional`).

---

## Backend: StreamBridge

For telephony integration, the Voice Agent repo exposes a **StreamBridge** class (`voice_agent.realtime.StreamBridge`) for backend use. It is not used by the default server; it is the integration point when the backend needs to connect PSTN/SIP media (e.g. Twilio Media Streams) to the same STT/TTS pipeline with an event-based protocol. Call `process_stream(websocket, call_id, business_id, business_name="...", call_type="inbound"|"outbound", reason=...)`. **`business_name` is required** (provision from onboarding); the greeting uses it, not business_id. See `voice_agent/README.md` (StreamBridge section) and `docs/integration/telephony_voice_agent.md` for how to integrate.

---

## Notes

- **Telephony:** The Voice Agent does **not** handle PSTN/SIP/calls. Backend/telephony gateway should send audio to Voice Agent (HTTP or WebSocket) and play back the response audio.
- **ffmpeg:** Optional; needed only if converting to non-MP3 formats (e.g. WAV/MULAW). MP3 from ElevenLabs works without ffmpeg.
- **ElevenLabs:** Requirements allow 1.x and exclude 2.x in `requirements.txt` (2.x can hit Windows long-path limits on install).
