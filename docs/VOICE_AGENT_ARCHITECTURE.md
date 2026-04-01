# Voice Agent Architecture

## Architecture Diagram

Full pipeline showing all components including the Prompt Processor.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           VOICE AGENT - FULL ARCHITECTURE                                │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                              AUDIO INPUT
                          (Caller / User Speech)
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        VOICE AGENT SERVICE                                  │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 1. WHISPER STT (Speech-to-Text)                                                    │  │
│  │    • Receives raw audio                                                            │  │
│  │    • Transcribes speech → text                                                     │  │
│  │    • OpenAI Whisper API                                                            │  │
│  └─────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                            │                                             │
│                                            ▼  (text)                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 2. AGENT ROUTER (Dialog Management)                                                │  │
│  │    • Receives transcribed text                                                     │  │
│  │    • Routes to Customer AI via POST /api/v1/chat                                   │  │
│  │    • Passes context: { channel: "voice", customer_id, ... }                        │  │
│  └─────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                            │                                             │
│                                            │  chat (text)                                │
└────────────────────────────────────────────┼─────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                                                    │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 3. CUSTOMER AI (Port 8000)                                                         │  │
│  │    • Receives message + context (channel: voice)                                   │  │
│  │    • Generates voice-optimized response:                                           │  │
│  │      - 3–5 short spoken sentences                                                  │  │
│  │      - No bullets/lists, simple words                                              │  │
│  │      - Nigerian English                                                            │  │
│  │    • Returns text response                                                         │  │
│  └─────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                            │                                             │
└────────────────────────────────────────────┼─────────────────────────────────────────────┘
                                             │  (AI response text)
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        VOICE AGENT SERVICE                                   │
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 4. PROMPT PROCESSOR (Response Optimization for Voice)                              │  │
│  │    • Converts bullets/lists → spoken prose                                         │  │
│  │    • Smart brevity: 3 sentences (simple) / 5 sentences (complex topics)             │  │
│  │    • Natural boundaries (no mid-thought cuts)                                      │  │
│  │    • Progressive disclosure: "Would you like me to go into more detail?"           │  │
│  │    • Nigerian English tone adjustments                                             │  │
│  │    • Micro-confirmations for critical details (time, money, location)              │  │
│  └─────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                            │                                             │
│                                            ▼  (processed text)                           │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 5. ELEVENLABS TTS (Text-to-Speech)                                                 │  │
│  │    • Synthesizes text → natural speech                                             │  │
│  │    • Nigerian English female voice                                                 │  │
│  │    • ElevenLabs API                                                                │  │
│  └─────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                            │                                             │
└────────────────────────────────────────────┼─────────────────────────────────────────────┘
                                             │
                                             ▼
                              AUDIO OUTPUT
                         (Synthesized Speech)
```

## Data Flow Summary

| Step | Component        | Input              | Output             |
|------|------------------|--------------------|--------------------|
| 1    | Whisper STT      | Audio              | Text (transcript)  |
| 2    | Agent Router     | Text               | Routes to Customer AI |
| 3    | Customer AI      | Text + context     | Text (voice-optimized response) |
| 4    | **Prompt Processor** | Text           | Text (TTS-ready, Nigerian tone) |
| 5    | ElevenLabs TTS   | Text               | Audio              |

## Component Details

### Prompt Processor

The Prompt Processor sits between Customer AI and TTS. It ensures responses are suitable for real-time voice:

- **Bullet-to-prose**: Converts markdown bullets/lists into flowing spoken prose
- **Smart brevity**: 3 sentences for simple topics, 5 for complex (policy, refund, procedure)
- **Progressive disclosure**: When content is trimmed, adds "Would you like me to go into more detail?"
- **Nigerian English**: Light-touch tone substitutions (e.g., "No wahala", "Kindly")
- **Micro-confirmations**: Adds "Is that correct?" when giving times, amounts, or addresses

**File**: `voice_agent/dialog/prompt_processor.py`
