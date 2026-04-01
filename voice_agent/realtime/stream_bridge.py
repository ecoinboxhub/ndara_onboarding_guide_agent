"""
WebSocket Audio Stream Bridge
Handles real-time audio streaming between telephony and voice processing pipeline
"""

import logging
import asyncio
import base64
import json
import time
from typing import Optional, Callable, Dict, Any, Deque
from collections import deque
from fastapi import WebSocket
from .stt_whisper import WhisperSTT
from .tts_elevenlabs import ElevenLabsTTS
from ..config import VoiceConfig
from ..dialog.greeting import get_greeting_text

logger = logging.getLogger(__name__)

class StreamBridge:
    """Bridge between telephony media streams and voice processing pipeline"""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self.stt = WhisperSTT(config)
        self.tts = ElevenLabsTTS(config)
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        
        # Latency optimization settings
        self.audio_buffer_size = 1600  # 200ms at 8kHz
        self.max_buffer_duration = 0.5  # 500ms max buffer
        self.voice_activity_threshold = 0.1  # 100ms silence threshold
        self.interrupt_threshold = 0.3  # 300ms to detect interruption
    
    async def process_stream(
        self,
        websocket: WebSocket,
        call_id: str,
        business_id: Optional[str] = None,
        business_name: str = "",
        call_type: Optional[str] = "inbound",
        reason: Optional[str] = None,
        on_audio_received: Optional[Callable] = None,
        on_audio_synthesized: Optional[Callable] = None
    ):
        """
        Process real-time audio stream from telephony media streams.

        Args:
            websocket: WebSocket connection
            call_id: Unique call identifier
            business_id: Business identifier (for routing/TTS)
            business_name: Display name from onboarding; required for greeting (not business_id)
            call_type: "inbound" | "outbound" for greeting and feature access
            reason: For outbound only (e.g. abandoned_cart, order_issues, technical_fixed, promotional)
            on_audio_received: Callback for received audio
            on_audio_synthesized: Callback for synthesized audio
        """
        if not business_name or not str(business_name).strip():
            raise ValueError("business_name is required for greeting (provision from onboarding)")
        try:
            # Initialize stream state with latency optimization
            stream_state = {
                "call_id": call_id,
                "business_id": business_id,
                "business_name": business_name.strip(),
                "call_type": call_type or "inbound",
                "reason": reason,
                "status": "active",
                "audio_buffer": b"",
                "audio_queue": deque(maxlen=10),  # Circular buffer for audio chunks
                "last_activity": asyncio.get_event_loop().time(),
                "voice_activity_start": None,
                "silence_duration": 0.0,
                "is_speaking": False,
                "interrupt_detected": False,
                "processing_latency": [],
                "total_audio_processed": 0
            }
            
            self.active_streams[call_id] = stream_state
            
            logger.info(f"Processing stream for call {call_id}")
            
            # Process WebSocket messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_stream_message(
                        call_id=call_id,
                        data=data,
                        on_audio_received=on_audio_received,
                        on_audio_synthesized=on_audio_synthesized
                    )
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message from call {call_id}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing message for call {call_id}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error processing stream for call {call_id}: {str(e)}")
        finally:
            await self._cleanup_stream(call_id)
    
    async def _handle_stream_message(
        self,
        call_id: str,
        data: Dict[str, Any],
        on_audio_received: Optional[Callable] = None,
        on_audio_synthesized: Optional[Callable] = None
    ):
        """Handle individual stream message"""
        try:
            event_type = data.get("event")
            
            if event_type == "connected":
                logger.info(f"Stream connected for call {call_id}")
                await self._handle_stream_connected(call_id, data)
                
            elif event_type == "start":
                logger.info(f"Stream started for call {call_id}")
                await self._handle_stream_start(call_id, data)
                
            elif event_type == "media":
                await self._handle_media_data(
                    call_id=call_id,
                    data=data,
                    on_audio_received=on_audio_received
                )
                
            elif event_type == "stop":
                logger.info(f"Stream stopped for call {call_id}")
                await self._handle_stream_stop(call_id, data)
                
            else:
                logger.debug(f"Unhandled event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling stream message for call {call_id}: {str(e)}")
    
    async def _handle_stream_connected(self, call_id: str, data: Dict[str, Any]):
        """Handle stream connected event"""
        try:
            stream_state = self.active_streams.get(call_id)
            if stream_state:
                stream_state["status"] = "connected"
                stream_state["stream_sid"] = data.get("streamSid")
                
        except Exception as e:
            logger.error(f"Error handling stream connected for call {call_id}: {str(e)}")
    
    async def _handle_stream_start(self, call_id: str, data: Dict[str, Any]):
        """Handle stream start event. Start payload may override call_type and reason."""
        try:
            stream_state = self.active_streams.get(call_id)
            if stream_state:
                stream_state["status"] = "active"
                stream_state["start_time"] = asyncio.get_event_loop().time()
                if "call_type" in data:
                    stream_state["call_type"] = data.get("call_type", "inbound")
                if "reason" in data:
                    stream_state["reason"] = data.get("reason")
                if data.get("business_name"):
                    stream_state["business_name"] = str(data["business_name"]).strip()
                # Send initial greeting (inbound vs outbound, with optional reason)
                await self._send_initial_greeting(
                    call_id,
                    stream_state.get("business_id"),
                    stream_state["business_name"],
                    stream_state.get("call_type", "inbound"),
                    stream_state.get("reason"),
                )
        except Exception as e:
            logger.error(f"Error handling stream start for call {call_id}: {str(e)}")
    
    async def _handle_media_data(
        self,
        call_id: str,
        data: Dict[str, Any],
        on_audio_received: Optional[Callable] = None
    ):
        """Handle media data from caller with latency optimization"""
        try:
            # Decode base64 audio data
            audio_payload = data.get("media", {}).get("payload")
            if not audio_payload:
                return
            
            audio_data = base64.b64decode(audio_payload)
            current_time = time.time()
            
            # Update stream state
            stream_state = self.active_streams.get(call_id)
            if not stream_state:
                return
                
            # Add to circular buffer for efficient processing
            stream_state["audio_queue"].append({
                "data": audio_data,
                "timestamp": current_time
            })
            
            # Update activity tracking
            stream_state["last_activity"] = current_time
            stream_state["total_audio_processed"] += len(audio_data)
            
            # Voice Activity Detection (VAD)
            voice_detected = self._detect_voice_activity(audio_data)
            
            if voice_detected:
                if not stream_state["is_speaking"]:
                    stream_state["voice_activity_start"] = current_time
                    stream_state["is_speaking"] = True
                    stream_state["silence_duration"] = 0.0
                else:
                    # Reset silence counter
                    stream_state["silence_duration"] = 0.0
            else:
                if stream_state["is_speaking"]:
                    stream_state["silence_duration"] += 0.02  # 20ms chunks
                    
                    # Check for end of speech
                    if stream_state["silence_duration"] >= self.voice_activity_threshold:
                        await self._process_complete_utterance(
                            call_id=call_id,
                            on_audio_received=on_audio_received
                        )
                        stream_state["is_speaking"] = False
                        stream_state["voice_activity_start"] = None
            
            # Process audio immediately for low latency
            if len(stream_state["audio_queue"]) >= 5:  # Process every 5 chunks
                await self._process_audio_chunks(
                    call_id=call_id,
                    on_audio_received=on_audio_received
                )
                    
        except Exception as e:
            logger.error(f"Error handling media data for call {call_id}: {str(e)}")
    
    async def _process_audio_buffer(
        self,
        call_id: str,
        audio_data: bytes,
        on_audio_received: Optional[Callable] = None
    ):
        """Process accumulated audio buffer"""
        try:
            # Transcribe audio
            transcript = await self.stt.transcribe_audio(audio_data)
            
            if transcript and on_audio_received:
                await on_audio_received(
                    call_id=call_id,
                    audio_data=audio_data,
                    timestamp=asyncio.get_event_loop().time()
                )
                
        except Exception as e:
            logger.error(f"Error processing audio buffer for call {call_id}: {str(e)}")
    
    async def _handle_stream_stop(self, call_id: str, data: Dict[str, Any]):
        """Handle stream stop event"""
        try:
            stream_state = self.active_streams.get(call_id)
            if stream_state:
                stream_state["status"] = "stopped"
                stream_state["end_time"] = asyncio.get_event_loop().time()
                
        except Exception as e:
            logger.error(f"Error handling stream stop for call {call_id}: {str(e)}")
    
    async def synthesize_response(
        self,
        call_id: str,
        response: str,
        business_id: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Synthesize response text to audio
        
        Args:
            call_id: Call identifier
            response: Text response to synthesize
            business_id: Business identifier for voice customization
            
        Returns:
            Audio bytes or None if synthesis failed
        """
        try:
            # Synthesize speech
            audio_data = await self.tts.synthesize_speech(
                text=response,
                business_id=business_id
            )
            
            if audio_data:
                # Send audio to caller
                await self.send_audio_to_caller(call_id, audio_data)
                
                logger.info(f"Synthesized response for call {call_id}: {response[:50]}...")
                return audio_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error synthesizing response for call {call_id}: {str(e)}")
            return None
    
    async def send_audio_to_caller(self, call_id: str, audio_data: bytes):
        """Send audio data to caller via WebSocket"""
        try:
            stream_state = self.active_streams.get(call_id)
            if not stream_state:
                logger.warning(f"No stream state found for call {call_id}")
                return
            
            # Convert audio to base64 for telephony gateway
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Create media message
            media_message = {
                "event": "media",
                "streamSid": stream_state.get("stream_sid"),
                "media": {
                    "payload": audio_b64
                }
            }
            
            # Send via WebSocket (implementation would depend on WebSocket connection)
            logger.info(f"Sent audio to caller for call {call_id}")
            
        except Exception as e:
            logger.error(f"Error sending audio to caller for call {call_id}: {str(e)}")
    
    async def _send_initial_greeting(
        self,
        call_id: str,
        business_id: Optional[str],
        business_name: str,
        call_type: str = "inbound",
        reason: Optional[str] = None,
    ):
        """Send initial greeting (introduction first). Uses business_name from onboarding, not business_id."""
        try:
            greeting_text = get_greeting_text(
                call_type=call_type,
                business_name=business_name,
                reason=reason,
            )
            await self.synthesize_response(
                call_id=call_id,
                response=greeting_text,
                business_id=business_id
            )
        except Exception as e:
            logger.error(f"Error sending initial greeting for call {call_id}: {str(e)}")
    
    async def transfer_to_human(
        self,
        call_sid: str,
        agent_contact: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Transfer call to human agent
        
        Args:
            call_sid: Call SID
            agent_contact: Human agent contact
            context: Transfer context
            
        Returns:
            Success status
        """
        try:
            # Implementation would use telephony provider to transfer call
            logger.info(f"Transferring call {call_sid} to {agent_contact}")
            return True
            
        except Exception as e:
            logger.error(f"Error transferring call {call_sid}: {str(e)}")
            return False
    
    async def _cleanup_stream(self, call_id: str):
        """Clean up stream state"""
        try:
            if call_id in self.active_streams:
                del self.active_streams[call_id]
                logger.info(f"Cleaned up stream for call {call_id}")
                
        except Exception as e:
            logger.error(f"Error cleaning up stream for call {call_id}: {str(e)}")
    
    def _detect_voice_activity(self, audio_data: bytes) -> bool:
        """Simple voice activity detection based on audio energy"""
        try:
            # Convert bytes to 16-bit PCM samples
            import struct
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            
            # Calculate RMS energy
            rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
            
            # Threshold for voice activity (adjustable)
            voice_threshold = 1000  # Adjust based on testing
            
            return rms > voice_threshold
            
        except Exception as e:
            logger.error(f"Error in voice activity detection: {str(e)}")
            return False
    
    async def _process_complete_utterance(
        self,
        call_id: str,
        on_audio_received: Optional[Callable] = None
    ):
        """Process complete utterance when speech ends"""
        try:
            stream_state = self.active_streams.get(call_id)
            if not stream_state:
                return
            
            # Combine all audio chunks from the utterance
            utterance_audio = b""
            for chunk in stream_state["audio_queue"]:
                utterance_audio += chunk["data"]
            
            if len(utterance_audio) > 0:
                # Process the complete utterance
                await self._process_audio_buffer(
                    call_id=call_id,
                    audio_data=utterance_audio,
                    on_audio_received=on_audio_received
                )
            
            # Clear the queue
            stream_state["audio_queue"].clear()
            
        except Exception as e:
            logger.error(f"Error processing complete utterance for call {call_id}: {str(e)}")
    
    async def _process_audio_chunks(
        self,
        call_id: str,
        on_audio_received: Optional[Callable] = None
    ):
        """Process audio chunks for real-time processing"""
        try:
            stream_state = self.active_streams.get(call_id)
            if not stream_state:
                return
            
            # Process recent chunks
            recent_chunks = list(stream_state["audio_queue"])[-3:]  # Last 3 chunks
            combined_audio = b"".join(chunk["data"] for chunk in recent_chunks)
            
            if len(combined_audio) > 0:
                # Quick processing for low latency
                start_time = time.time()
                
                # Transcribe with streaming for low latency
                transcription = await self.stt.transcribe_streaming(combined_audio)
                
                processing_time = time.time() - start_time
                stream_state["processing_latency"].append(processing_time)
                
                # Keep only last 10 latency measurements
                if len(stream_state["processing_latency"]) > 10:
                    stream_state["processing_latency"] = stream_state["processing_latency"][-10:]
                
                if transcription and transcription.strip():
                    logger.info(f"Real-time transcription for call {call_id}: {transcription}")
                    
                    if on_audio_received:
                        await on_audio_received(call_id, transcription)
            
        except Exception as e:
            logger.error(f"Error processing audio chunks for call {call_id}: {str(e)}")
    
    def get_latency_stats(self, call_id: str) -> Dict[str, Any]:
        """Get latency statistics for a call"""
        stream_state = self.active_streams.get(call_id)
        if not stream_state:
            return {}
        
        latencies = stream_state.get("processing_latency", [])
        if not latencies:
            return {}
        
        return {
            "avg_latency": sum(latencies) / len(latencies),
            "min_latency": min(latencies),
            "max_latency": max(latencies),
            "total_audio_processed": stream_state.get("total_audio_processed", 0),
            "is_speaking": stream_state.get("is_speaking", False)
        }

