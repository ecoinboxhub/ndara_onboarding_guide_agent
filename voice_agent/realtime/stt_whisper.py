"""
OpenAI Whisper Speech-to-Text Integration
"""

import audioop
import io
import logging
from typing import Optional
from openai import AsyncOpenAI
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class WhisperSTT:
    """OpenAI Whisper client for real-time transcription"""
    
    def __init__(self, config):
        self.config = config
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.model = "whisper-1"  # OpenAI's Whisper API model
    
    def _is_whisper_native_format(self, audio_data: bytes) -> Optional[str]:
        """
        Detect if audio is already in a format Whisper accepts (no ffmpeg needed).
        Returns file extension (e.g. 'mp3', 'wav') or None if conversion required.
        """
        if len(audio_data) < 12:
            return None
        # MP3: ID3 tag or frame sync 0xFF 0xFB / 0xFF 0xFA / 0xFF 0xF3
        if audio_data[:3] == b"ID3" or (audio_data[0] == 0xFF and (audio_data[1] & 0xE0) == 0xE0):
            return "mp3"
        # WAV: RIFF....WAVE
        if audio_data[:4] == b"RIFF" and audio_data[8:12] == b"WAVE":
            return "wav"
        # WebM / MKV: EBML header
        if audio_data[:4] == b"\x1a\x45\xdf\xa3":
            return "webm"
        # M4A / MP4: ftyp
        if audio_data[4:8] == b"ftyp" and len(audio_data) >= 12:
            return "m4a"
        return None

    def _prepare_audio_for_whisper(self, audio_data: bytes) -> Optional[io.BytesIO]:
        """
        Prepare audio for Whisper API. If input is already MP3/WAV/WebM/M4A, pass through
        without ffmpeg. Otherwise convert from MULAW/PCM (requires ffmpeg for export).
        """
        ext = self._is_whisper_native_format(audio_data)
        if ext:
            buf = io.BytesIO(audio_data)
            buf.name = f"audio.{ext}"
            return buf
        return self._convert_audio_for_whisper(audio_data)

    async def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio data to text using OpenAI Whisper
        
        Args:
            audio_data: Raw audio bytes (MP3/WAV/WebM uploads, or MULAW for telephony)
            
        Returns:
            Transcribed text or None if no speech detected
        """
        try:
            audio_file = self._prepare_audio_for_whisper(audio_data)
            
            if not audio_file:
                logger.warning("Failed to convert audio for Whisper")
                return None
            
            # Transcribe using Whisper API
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language="en",  # English (supports Nigerian English naturally)
                response_format="text"
            )
            
            transcript = response.strip() if isinstance(response, str) else response.text.strip()
            
            if transcript:
                logger.info(f"Whisper transcription: {transcript}")
                return transcript
            
            return None
            
        except Exception as e:
            logger.error(f"Error transcribing audio with Whisper: {str(e)}")
            return None
    
    async def transcribe_streaming(self, audio_data: bytes) -> Optional[str]:
        """
        Quick wrapper to perform low-latency single-chunk transcription.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text or None
        """
        return await self.transcribe_audio(audio_data)
    
    def _convert_audio_for_whisper(self, audio_data: bytes) -> Optional[io.BytesIO]:
        """
        Convert MULAW or PCM audio to MP3 format for Whisper API.
        Telephony typically sends 8kHz MULAW mono; we convert to linear PCM first.
        """
        try:
            sample_rate = getattr(self.config, "STT_SAMPLE_RATE", 8000)
            # Convert MULAW to 16-bit linear PCM (pydub expects PCM, not MULAW)
            try:
                pcm_data = audioop.ulaw2lin(audio_data, 2)  # 2 = 16-bit output
            except audioop.error:
                # May already be PCM (e.g. LINEAR16); use as-is
                pcm_data = audio_data
            sample_width = 2  # 16-bit
            audio = AudioSegment(
                data=pcm_data,
                sample_width=sample_width,
                frame_rate=sample_rate,
                channels=1
            )
            if sample_rate < 16000:
                audio = audio.set_frame_rate(16000)  # Upsample for better transcription
            
            # Export as MP3 (Whisper accepts MP3, WAV, etc.)
            buffer = io.BytesIO()
            audio.export(buffer, format="mp3", bitrate="128k")
            buffer.seek(0)
            
            # Set filename for OpenAI API
            buffer.name = "audio.mp3"
            
            return buffer
            
        except Exception as e:
            logger.error(f"Error converting audio for Whisper: {str(e)}")
            return None
    
    async def detect_speech_activity(self, audio_data: bytes) -> bool:
        """
        Detect if audio contains speech
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            True if speech detected, False otherwise
        """
        try:
            # Simple approach: try to transcribe and see if we get text
            transcript = await self.transcribe_audio(audio_data)
            return bool(transcript and len(transcript.strip()) > 0)
            
        except Exception as e:
            logger.error(f"Error detecting speech activity: {str(e)}")
            return False
    
    async def get_confidence_score(self, audio_data: bytes) -> float:
        """
        Get confidence score for audio transcription
        Note: OpenAI Whisper API doesn't return confidence scores,
        so we return 1.0 if transcription succeeds, 0.0 otherwise
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Confidence score (1.0 or 0.0)
        """
        try:
            transcript = await self.transcribe_audio(audio_data)
            return 1.0 if transcript else 0.0
            
        except Exception as e:
            logger.error(f"Error getting confidence score: {str(e)}")
            return 0.0
