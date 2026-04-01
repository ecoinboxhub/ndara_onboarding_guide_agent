"""
Automated tests for Voice Agent HTTP endpoints.
Run from repo root: pytest voice_agent/tests/ -v
Or from voice_agent with parent on PYTHONPATH: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient


class TestRootAndHealth:
    """Tests for service info and health."""

    def test_get_root(self, client: TestClient):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data.get("service") == "Voice Agent - AI Audio Processing"
        assert "version" in data
        assert data.get("status") == "operational"
        assert "docs" in data

    def test_health(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "healthy"
        comp = data.get("components", {})
        assert "whisper_stt" in comp
        assert "elevenlabs_tts" in comp
        assert "customer_ai" in comp


class TestWhisperEndpoints:
    """Tests for STT (Whisper) test endpoints."""

    def test_whisper_test_info(self, client: TestClient):
        r = client.get("/whisper/test/info")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "success"
        stt = data.get("stt", {})
        assert stt.get("provider") == "OpenAI"
        assert stt.get("model") == "whisper-1"
        assert "sample_rate" in stt
        assert "supported_input_formats" in stt or "supported_input" in stt

    def test_whisper_test_empty_file_rejected(self, client: TestClient):
        """Upload empty file -> 400."""
        r = client.post(
            "/whisper/test",
            files={"audio_file": ("empty.mp3", b"", "audio/mpeg")},
        )
        assert r.status_code == 400

    def test_whisper_test_missing_file_rejected(self, client: TestClient):
        """No audio_file -> 422 (validation error)."""
        r = client.post("/whisper/test", data={})
        assert r.status_code == 422


class TestVoiceEndpoints:
    """Tests for TTS (voice) test endpoints. May fail if ElevenLabs key invalid."""

    def test_voice_test_info(self, client: TestClient):
        r = client.get("/voice/test/info")
        # 200 if key valid and voices_read permission; 500 possible if key invalid
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            data = r.json()
            assert data.get("status") == "success"
            assert "current_voice" in data

    def test_voice_test_empty_text_rejected(self, client: TestClient):
        r = client.post(
            "/voice/test",
            json={"text": "   ", "format": "MP3"},
        )
        assert r.status_code == 400


class TestMetrics:
    """Tests for metrics endpoint."""

    def test_metrics(self, client: TestClient):
        r = client.get("/metrics")
        # 200 if ENABLE_METRICS true, 404 if disabled
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            data = r.json()
            assert "recent_turns" in data or "latest_status" in data or "recent_completions" in data
