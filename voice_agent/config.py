"""
Voice Agent Configuration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class VoiceConfig(BaseSettings):
    """Voice Agent Configuration"""
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow",
    )
    
    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8003, description="Server port")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # OpenAI Configuration (for Whisper STT)
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key for Whisper")
    
    # ElevenLabs Configuration (for TTS)
    ELEVENLABS_API_KEY: str = Field(..., description="ElevenLabs API key")
    ELEVENLABS_VOICE_ID: str = Field(..., description="ElevenLabs voice ID for Nigerian English female voice")
    
    # Audio Processing Settings
    AUDIO_SAMPLE_RATE: int = Field(default=16000, description="Audio sample rate for processing")
    STT_SAMPLE_RATE: int = Field(default=8000, description="STT input sample rate (8kHz for telephony MULAW)")
    TTS_SAMPLE_RATE: int = Field(default=8000, description="TTS output sample rate for telephony (8kHz MULAW)")
    AUDIO_CHANNELS: int = Field(default=1, description="Audio channels (1=mono, 2=stereo)")
    AUDIO_CHUNK_SIZE: int = Field(default=1024, description="Audio chunk size for streaming")
    
    # Performance Settings
    MAX_TURN_LATENCY: float = Field(default=2.0, description="Max turn latency in seconds")
    WEBSOCKET_TIMEOUT: int = Field(default=60, description="WebSocket timeout in seconds")
    SESSION_TIMEOUT: int = Field(default=1800, description="Session timeout in seconds (30 min)")
    
    # Customer AI Integration
    CUSTOMER_AI_BASE_URL: str = Field(default="http://localhost:8000", description="Customer AI base URL")
    CUSTOMER_AI_API_KEY: str = Field(default="dev-key-12345", description="Customer AI API key")
    
    # Session Management
    ENABLE_METRICS: bool = Field(default=True, description="Enable basic metrics")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
