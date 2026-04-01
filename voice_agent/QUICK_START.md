# Voice Agent - Quick Start Guide

## Prerequisites

- Python 3.8+
- OpenAI API key (for Whisper STT)
- ElevenLabs API key + Voice ID (for TTS)
- Customer AI running on port 8000

## 5-Minute Setup

### Step 1: Configure Environment

Create/update `.env` file in the project root:

```env
# OpenAI for Speech-to-Text
OPENAI_API_KEY=sk-your-key-here

# ElevenLabs for Text-to-Speech
ELEVENLABS_API_KEY=your-elevenlabs-key
ELEVENLABS_VOICE_ID=your-voice-id

# AI Services (if different from defaults)
CUSTOMER_AI_BASE_URL=http://localhost:8000
CUSTOMER_AI_API_KEY=dev-key-12345
```

### Step 2: Install Dependencies

```bash
cd voice_agent
pip install --upgrade pip   # See repo SECURITY.md (pip tar/symlink fix)
pip install -r requirements.txt
```

### Step 3: Start the Service

```bash
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8003
```

### Step 4: Test via cURL

```bash
# Test TTS
curl -X POST http://localhost:8003/voice/test \
  -H "Content-Type: application/json" \
  -d '{"text": "Good day! How may I help you?", "format": "MP3"}' \
  --output test_voice.mp3

# Test STT (upload audio, get transcript)
curl -X POST http://localhost:8003/whisper/test -F "audio_file=@recording.mp3"

# Process audio file (full pipeline)
curl -X POST http://localhost:8003/audio/process \
  -F "audio_file=@recording.mp3" \
  -F "business_id=beauty_wellness_001" \
  --output ai_response.mp3
```

## Testing Options

### Option 1: cURL
- Use the commands above to test TTS and audio processing
- See `/docs` for full API documentation

### Option 2: API Client
- Use Postman, curl, or your preferred HTTP client
- See README for endpoint details

## API Testing (Optional)

### Test Voice Synthesis (TTS)
```bash
curl -X POST http://localhost:8003/voice/test \
  -H "Content-Type: application/json" \
  -d '{"text": "Good day! How may I help you?", "format": "MP3"}' \
  --output voice_test.mp3

# Play the audio
start voice_test.mp3  # Windows
# open voice_test.mp3  # macOS
# xdg-open voice_test.mp3  # Linux
```

### Test Speech-to-Text (STT)
```bash
curl -X POST http://localhost:8003/whisper/test -F "audio_file=@recording.mp3"
# Returns JSON with "transcript", "status", "filename", "size_bytes"
```

### Test Full Pipeline
```bash
# First, record audio or download a sample
# Then process it:
curl -X POST http://localhost:8003/audio/process \
  -F "audio_file=@recording.mp3" \
  -F "business_id=beauty_wellness_001" \
  --output ai_response.mp3

# Play the response
start ai_response.mp3
```

## Troubleshooting

### "Failed to transcribe audio"
**Solutions**:
- Check your OpenAI API key is valid
- Ensure you have credits in your OpenAI account
- Verify the audio file isn't corrupted

### "Failed to synthesize speech"
**Solutions**:
- Check your ElevenLabs API key and voice ID
- Verify you have credits in your ElevenLabs account
- Ensure the voice ID exists in your account

### "Customer AI not connected"
**Solutions**:
- Make sure Customer AI is running: `python customer_ai/main.py`
- Check it's accessible at `http://localhost:8000`
- Verify the API key matches in both services

### Port 8003 already in use
**Solution**: 
```bash
# Change port in .env
VOICE_AGENT_PORT=8004

# Or kill the process using port 8003
netstat -ano | findstr :8003  # Windows
lsof -i :8003  # macOS/Linux
```

## What's Happening Behind the Scenes

When you process audio:

1. **Speech-to-Text**: OpenAI Whisper transcribes your audio → text
2. **AI Dialog**: Text sent to Customer AI
3. **Prompt Processing**: Response adjusted for Nigerian English tone
4. **Text-to-Speech**: ElevenLabs synthesizes AI response → audio

## Next Steps

- **Test different scenarios**: Appointments, orders, complaints, inquiries
- **Try both businesses**: Beauty spa vs Restaurant
- **Multiple turns**: Use session API for full conversations

## Production Deployment

For production use:

1. **Get production API keys** (not development keys)
2. **Set up proper environment** variables
3. **Use production server** (Gunicorn, not uvicorn directly)
4. **Set up HTTPS** for secure connections
5. **Configure rate limiting** and monitoring
6. **Scale horizontally** as needed

## Documentation

- **Full API Docs**: http://localhost:8003/docs
- **README**: `voice_agent/README.md`
- **Walkthrough**: See artifacts for detailed changes

## Support

For issues, check:
1. Logs in terminal where you ran `python main.py`
2. API documentation at `/docs`

Happy testing! 🎙️
