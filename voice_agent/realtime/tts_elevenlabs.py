"""
ElevenLabs Text-to-Speech Integration.

Runtime-compatible with ElevenLabs Python SDK 1.x and 2.x API styles.
Requirements allow 1.x and exclude 2.x (see voice_agent/requirements.txt)
because SDK 2.x can fail to install on Windows due to long-path limits.
"""

import logging
import io
from typing import Optional, Dict, Any
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def _synthesize_audio(client, voice_id: str, text: str, voice_settings: Optional[dict] = None) -> bytes:
    """Generate audio using ElevenLabs - supports SDK 1.x and 2.x."""
    vs = voice_settings or {}
    # SDK 2.x: client.text_to_speech.convert()
    try:
        if hasattr(client, "text_to_speech") and hasattr(client.text_to_speech, "convert"):
            kwargs = {
                "voice_id": voice_id,
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "output_format": "mp3_44100_128",
            }
            if vs:
                kwargs["voice_settings"] = vs
            resp = client.text_to_speech.convert(**kwargs)
            if hasattr(resp, "__iter__") and not isinstance(resp, (bytes, bytearray)):
                return b"".join(resp)
            return resp if isinstance(resp, (bytes, bytearray)) else bytes(resp)
    except Exception:
        pass
    # SDK 1.x / 0.2.x: client.generate()
    try:
        from elevenlabs import VoiceSettings
        gen = client.generate(
            text=text,
            voice=voice_id,
            model="eleven_turbo_v2",
            voice_settings=VoiceSettings(**vs) if vs else None,
        )
        return b"".join(gen)
    except Exception:
        gen = client.generate(text=text, voice=voice_id, model="eleven_turbo_v2")
        return b"".join(gen)


class ElevenLabsTTS:
    """ElevenLabs client for voice synthesis"""
    
    def __init__(self, config):
        self.config = config
        self.client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
        self.voice_id = config.ELEVENLABS_VOICE_ID
        # TTS sample rate for telephony (default 8kHz for MULAW)
        self.tts_sample_rate = getattr(config, "TTS_SAMPLE_RATE", 8000)
    
    async def synthesize_speech(
        self,
        text: str,
        business_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        output_format: str = "MULAW"
    ) -> Optional[bytes]:
        """
        Synthesize text to speech using ElevenLabs
        
        Args:
            text: Text to synthesize
            business_id: Business identifier for voice customization (not used with ElevenLabs)
            agent_name: Agent name for personalization (not used with ElevenLabs)
            output_format: Audio format - "MULAW", "MP3", "LINEAR16" (WAV)
            
        Returns:
            Audio bytes or None if synthesis failed
        """
        try:
            voice_settings = {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
            audio_chunks = _synthesize_audio(self.client, self.voice_id, text, voice_settings)
            
            if not audio_chunks:
                logger.error("No audio generated from ElevenLabs")
                return None
            
            # ElevenLabs returns MP3 by default
            # Convert to requested format if needed
            if output_format.upper() in ["MULAW", "LINEAR16", "WAV"]:
                audio_data = self._convert_audio_format(audio_chunks, output_format)
            else:
                # Return MP3 as-is
                audio_data = audio_chunks
            
            logger.info(f"ElevenLabs synthesized: {text[:50]}... (format: {output_format})")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error synthesizing speech with ElevenLabs: {str(e)}")
            return None
    
    def _convert_audio_format(self, mp3_data: bytes, target_format: str) -> Optional[bytes]:
        """
        Convert MP3 audio to target format
        
        Args:
            mp3_data: MP3 audio bytes from ElevenLabs
            target_format: Target format (MULAW, LINEAR16, WAV)
            
        Returns:
            Converted audio bytes or None
        """
        try:
            # Load MP3 audio
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
            
            # Convert to target format
            if target_format.upper() == "MULAW":
                # Convert to MULAW for telephony
                # Set to 8kHz mono for telephony
                audio = audio.set_frame_rate(self.tts_sample_rate)
                audio = audio.set_channels(1)  # Mono
                audio = audio.set_sample_width(1)  # 8-bit for MULAW
                
                # Export as raw MULAW
                buffer = io.BytesIO()
                audio.export(buffer, format="mulaw", codec="pcm_mulaw")
                return buffer.getvalue()
                
            elif target_format.upper() in ["LINEAR16", "WAV"]:
                # Export as WAV with LINEAR16 encoding
                buffer = io.BytesIO()
                audio.export(buffer, format="wav", codec="pcm_s16le")
                return buffer.getvalue()
            
            else:
                logger.warning(f"Unknown target format: {target_format}, returning MP3")
                return mp3_data
                
        except Exception as e:
            logger.error(f"Error converting audio format: {str(e)}")
            return None
    
    async def synthesize_with_emotion(
        self,
        text: str,
        emotion: str = "neutral",
        business_id: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Synthesize speech with emotional tone
        
        Args:
            text: Text to synthesize
            emotion: Emotional tone (neutral, friendly, urgent, apologetic)
            business_id: Business identifier
            
        Returns:
            Audio bytes or None if synthesis failed
        """
        try:
            emotion_settings = self._get_emotion_settings(emotion)
            audio_chunks = _synthesize_audio(self.client, self.voice_id, text, emotion_settings)
            
            # Convert to MULAW for telephony
            audio_data = self._convert_audio_format(audio_chunks, "MULAW")
            
            logger.info(f"ElevenLabs synthesized with {emotion} emotion: {text[:50]}...")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error synthesizing speech with emotion: {str(e)}")
            return None
    
    def _get_emotion_settings(self, emotion: str) -> Dict[str, Any]:
        """
        Get voice settings for specific emotion
        
        Args:
            emotion: Emotion type (neutral, friendly, urgent, apologetic)
            
        Returns:
            Voice settings dictionary
        """
        emotion_configs = {
            "friendly": {
                "stability": 0.4,
                "similarity_boost": 0.8,
                "style": 0.3,
                "use_speaker_boost": True
            },
            "urgent": {
                "stability": 0.6,
                "similarity_boost": 0.7,
                "style": 0.6,
                "use_speaker_boost": True
            },
            "apologetic": {
                "stability": 0.7,
                "similarity_boost": 0.7,
                "style": 0.1,
                "use_speaker_boost": True
            },
            "neutral": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        return emotion_configs.get(emotion, emotion_configs["neutral"])
    
    async def cache_common_phrases(self, phrases: list):
        """
        Cache common phrases for faster response
        Note: With ElevenLabs' fast API, caching may not be as critical
        
        Args:
            phrases: List of common phrases to cache
        """
        try:
            for phrase in phrases:
                audio = await self.synthesize_speech(phrase)
                if audio:
                    # Store in cache (implementation would use Redis or similar)
                    logger.info(f"Cached phrase: {phrase[:30]}...")
                    
        except Exception as e:
            logger.error(f"Error caching phrases: {str(e)}")
    
    async def get_voice_characteristics(self) -> Dict[str, Any]:
        """
        Get available voice characteristics
        
        Returns:
            Voice information including current voice ID and available voices
        """
        try:
            # Get available voices (SDK 2.x: voices.search() or get_all())
            try:
                voices_response = self.client.voices.get_all()
            except AttributeError:
                voices_response = self.client.voices.search()
            voices_list = getattr(voices_response, "voices", voices_response)
            if not isinstance(voices_list, list):
                voices_list = list(voices_list) if hasattr(voices_list, "__iter__") and not isinstance(voices_list, (str, bytes)) else [voices_list]
            
            available_voices = []
            for v in voices_list:
                v_id = v.get("voice_id", "unknown") if isinstance(v, dict) else getattr(v, "voice_id", "unknown")
                v_name = v.get("name", "Unknown") if isinstance(v, dict) else getattr(v, "name", "Unknown")
                v_cat = v.get("category", "unknown") if isinstance(v, dict) else getattr(v, "category", "unknown")
                v_desc = v.get("description", "") if isinstance(v, dict) else getattr(v, "description", "")
                available_voices.append({"voice_id": v_id, "name": v_name, "category": v_cat, "description": v_desc})
            
            # Find current voice details
            current_voice = next(
                (v for v in available_voices if v["voice_id"] == self.voice_id),
                None
            )
            
            return {
                "available_voices": available_voices,
                "current_voice": current_voice or {"voice_id": self.voice_id, "name": "Custom Voice"},
                "voice_id": self.voice_id,
                "provider": "ElevenLabs"
            }
            
        except Exception as e:
            logger.error(f"Error getting voice characteristics: {str(e)}")
            return {
                "current_voice": {"voice_id": self.voice_id, "name": "Custom Voice"},
                "voice_id": self.voice_id,
                "provider": "ElevenLabs"
            }
