"""
Pytest fixtures for Voice Agent tests.
Sets minimal env so VoiceConfig loads; tests that call external APIs (ElevenLabs, OpenAI)
may still fail or be skipped if keys are invalid.
"""
import os
import sys
from pathlib import Path

import pytest

# Ensure voice_agent is importable (run from repo root or voice_agent)
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Minimal env for app creation (avoids ValidationError; real keys needed for TTS/STT calls)
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-for-tests")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy-for-tests")
os.environ.setdefault("ELEVENLABS_VOICE_ID", "test-voice-id")


@pytest.fixture
def app():
    """Create Voice Agent FastAPI app with test config."""
    from voice_agent.config import VoiceConfig
    from voice_agent.app import create_voice_app
    config = VoiceConfig()
    return create_voice_app(config)


@pytest.fixture
def client(app):
    """Test client for Voice Agent HTTP endpoints."""
    from fastapi.testclient import TestClient
    return TestClient(app)
