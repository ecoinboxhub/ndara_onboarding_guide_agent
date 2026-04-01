"""
Voice Agent FastAPI Application
Pure AI Audio Processing Service - No Telephony Integration
"""

import asyncio
import base64
import io
import json
import logging
import threading
import time
import uuid
import httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from .dialog.agent_router import AgentRouter
from .dialog.greeting import get_greeting_text
from .dialog.prompt_processor import PromptProcessor
from .realtime.stt_whisper import WhisperSTT
from .realtime.tts_elevenlabs import ElevenLabsTTS
from .analytics.quality_metrics import QualityMetrics
from .config import VoiceConfig

logger = logging.getLogger(__name__)

# Active audio sessions
active_sessions: Dict[str, Dict[str, Any]] = {}

# Per-session locks to serialize concurrent updates (e.g. multiple WebSockets sharing same session_id)
_session_locks: Dict[str, asyncio.Lock] = {}

# Call summaries: {session_id: {"summary": str, "expires_at": datetime}}
CALL_SUMMARY_TTL_SECONDS = 86400  # 24 hours
call_summaries: Dict[str, Dict[str, Any]] = {}
_call_summaries_lock: Optional[asyncio.Lock] = None
_call_summaries_lock_init = threading.Lock()


def _get_call_summaries_lock() -> asyncio.Lock:
    """Lazy-init asyncio.Lock (must be created inside event loop)."""
    global _call_summaries_lock
    with _call_summaries_lock_init:
        if _call_summaries_lock is None:
            _call_summaries_lock = asyncio.Lock()
    return _call_summaries_lock


async def _generate_call_summary(history: list, config: VoiceConfig) -> str:
    """Generate natural-language summary from conversation history using OpenAI."""
    if not history:
        return "No conversation recorded."
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        lines = []
        for turn in history:
            u = turn.get("user") or turn.get("message", "")
            a = turn.get("ai") or turn.get("response", "")
            if u:
                lines.append(f"Customer: {u}")
            if a:
                lines.append(f"Agent: {a}")
        transcript = "\n".join(lines) if lines else str(history)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarize this customer service call in 2-4 concise sentences for record-keeping. Focus on: what the customer needed, what was resolved or next steps."},
                {"role": "user", "content": transcript}
            ],
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Could not generate AI summary: {e}. Using fallback.")
        parts = []
        for h in history[:5]:
            u, a = h.get("user", ""), h.get("ai", "")
            if u or a:
                parts.append(f"{str(u)[:50]}: {str(a)[:50]}")
        return " | ".join(parts) if parts else "Call completed."


def _prune_expired_summaries():
    """Remove expired call summaries. Must be called while holding _call_summaries_lock."""
    now = datetime.utcnow()
    # Use datetime.max as default so entries missing expires_at are not purged (robust to future changes)
    expired = [k for k, v in call_summaries.items() if v.get("expires_at", datetime.max) <= now]
    for k in expired:
        del call_summaries[k]


def create_voice_app(config: VoiceConfig) -> FastAPI:
    """Create and configure FastAPI app for voice agent"""
    
    app = FastAPI(
        title="Voice Agent API",
        description="AI-powered voice processing service - STT, Dialog, TTS",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS middleware (allow_credentials must be False when using wildcard origins per CORS spec)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize components
    stt_service = WhisperSTT(config)
    tts_service = ElevenLabsTTS(config)
    agent_router = AgentRouter(config)
    prompt_processor = PromptProcessor(turn_budget_seconds=config.MAX_TURN_LATENCY)
    quality_metrics = QualityMetrics(config)
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "service": "Voice Agent - AI Audio Processing",
            "version": "2.0.0",
            "status": "operational",
            "docs": "/docs"
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "components": {
                "whisper_stt": "available",
                "elevenlabs_tts": "available",
                "customer_ai": "configured"
            }
        }
    
    # ==================== ONBOARDING (proxies to Customer AI) ====================
    
    @app.post("/api/v1/onboard")
    async def onboard_business(
        request: Request,
        business_id: Optional[str] = None
    ):
        """
        Onboard a business for voice and chat.
        
        Same knowledge base as Customer AI - proxies to Customer AI.
        Supports:
        1. POST /api/v1/onboard?business_id=1 with KnowledgeData in body
        2. Legacy: business_id in body with business_data
        """
        try:
            body = await request.json()
            result = await agent_router.onboard_business(business_id=business_id, body=body)
            return result
        except httpx.HTTPStatusError as e:
            detail = e.response.text
            try:
                detail = e.response.json().get("detail", detail)
            except Exception:
                pass
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in onboard proxy: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==================== AUDIO PROCESSING ENDPOINTS ====================
    
    class AudioProcessRequest(BaseModel):
        text: Optional[str] = None
        session_id: Optional[str] = None
        business_id: str
        
    @app.post("/audio/process")
    async def process_audio(
        audio_file: UploadFile = File(...),
        business_id: str = Form("default"),
        session_id: Optional[str] = Form(None),
        customer_id: Optional[str] = Form(None),
        conversation_id: Optional[str] = Form(None),
        call_type: Optional[str] = Form("inbound"),
    ):
        """
        Process audio file: STT → Dialog → TTS

        Upload an audio file, get back AI response as audio.
        Pass call_type (inbound|outbound) for feature access handling.
        """
        t0 = time.perf_counter()
        try:
            audio_data = await audio_file.read()
            transcript = await stt_service.transcribe_audio(audio_data)
            if not transcript:
                raise HTTPException(status_code=400, detail="Could not transcribe audio")
            logger.info(f"Transcribed: {transcript}")
            sess = active_sessions.get(session_id) if session_id else None
            routing_business_id = (sess and sess.get("business_id")) or business_id
            call_type_val = call_type or (sess and sess.get("call_type")) or "inbound"
            context = {
                "channel": "voice",
                "session_id": session_id,
                "business_id": routing_business_id,
                "customer_id": customer_id or (sess and sess.get("customer_id")),
                "conversation_id": conversation_id or (sess and sess.get("conversation_id")),
                "call_type": call_type_val,
            }
            result = await agent_router.route_message(
                call_id=session_id or str(uuid.uuid4()),
                business_id=routing_business_id,
                message=transcript,
                context=context
            )
            if not result:
                ai_text = "I'm sorry, I'm having trouble processing your request."
                esc_required, esc_payload = False, None
            else:
                ai_text = result.get("response", "")
                esc_required = result.get("escalation_required", False)
                esc_payload = result.get("escalation")
                if not esc_required and not ai_text:
                    ai_text = "I'm sorry, I'm having trouble processing your request."
            if esc_required:
                processed_response = ai_text or ""
                response_audio = b""
            else:
                processed_response = prompt_processor.process_response(context, ai_text)
                logger.info(f"AI Response: {processed_response}")
                response_audio = await tts_service.synthesize_speech(
                    text=processed_response,
                    output_format="MP3"
                )
                if not response_audio:
                    raise HTTPException(status_code=500, detail="Failed to synthesize speech")
            headers = {
                "X-Transcript": transcript,
                "X-Response-Text": processed_response,
                "X-Escalation-Required": str(esc_required).lower(),
                "Content-Disposition": 'attachment; filename="response.mp3"'
            }
            if esc_required and esc_payload:
                headers["X-Escalation-Payload"] = json.dumps(esc_payload)
            call_id = session_id or str(uuid.uuid4())
            turn_count = 1
            if session_id and session_id in active_sessions:
                lock = _session_locks.setdefault(session_id, asyncio.Lock())
                async with lock:
                    if session_id in active_sessions:
                        active_sessions[session_id]["turn_count"] += 1
                        turn_count = active_sessions[session_id]["turn_count"]
                        active_sessions[session_id]["conversation_history"].append({
                            "user": transcript,
                            "ai": processed_response,
                            "timestamp": datetime.now().isoformat()
                        })
            if config.ENABLE_METRICS:
                processing_time = time.perf_counter() - t0
                quality_metrics.record_turn(
                    call_id=call_id,
                    turn_count=turn_count,
                    transcript_length=len(transcript or ""),
                    processing_time=processing_time,
                )
            return Response(content=response_audio, media_type="audio/mpeg", headers=headers)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    class SessionStartRequest(BaseModel):
        business_id: str
        business_name: str  # Display name from onboarding; required for greeting (not business_id)
        customer_id: Optional[str] = None
        conversation_id: Optional[str] = None
        call_type: Optional[str] = "inbound"  # inbound | outbound for feature access
        reason: Optional[str] = None  # for outbound: abandoned_cart, order_issues, technical_fixed, promotional, etc.
        metadata: Optional[Dict[str, Any]] = None

    @app.post("/audio/session/start")
    async def start_audio_session(request: SessionStartRequest):
        """
        Start a new audio conversation session.

        business_name is required (provision from onboarding); it is used in the greeting, not business_id.
        Pass call_type (inbound|outbound) and optional reason for outbound to customize the first utterance.
        """
        try:
            session_id = str(uuid.uuid4())
            call_type = request.call_type or "inbound"
            active_sessions[session_id] = {
                "session_id": session_id,
                "business_id": request.business_id,
                "business_name": request.business_name,
                "customer_id": request.customer_id,
                "conversation_id": request.conversation_id,
                "call_type": call_type,
                "reason": request.reason,
                "metadata": request.metadata or {},
                "created_at": datetime.now().isoformat(),
                "conversation_history": [],
                "turn_count": 0
            }
            greeting_text = get_greeting_text(
                call_type=call_type,
                business_name=request.business_name,
                reason=request.reason,
            )
            logger.info(f"Started session {session_id} for business {request.business_id}")
            return {
                "session_id": session_id,
                "status": "active",
                "business_id": request.business_id,
                "greeting": {
                    "call_type": call_type,
                    "text": greeting_text,
                }
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error starting session: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/audio/greeting")
    async def get_audio_greeting(
        business_name: str,
        call_type: str = "inbound",
        reason: Optional[str] = None,
        include_audio: bool = False,
    ):
        """
        Get the first-utterance (greeting) text and optionally synthesized audio.
        business_name is required (provision from onboarding). For outbound, pass reason.
        """
        try:
            call_type_val = (call_type or "inbound").strip().lower()
            text = get_greeting_text(
                call_type=call_type_val,
                business_name=business_name,
                reason=reason,
            )
            out = {"call_type": call_type_val, "text": text}
            if include_audio:
                audio_bytes = await tts_service.synthesize_speech(
                    text=text,
                    output_format="MP3"
                )
                if audio_bytes:
                    out["audio_base64"] = base64.b64encode(audio_bytes).decode("utf-8")
            return out
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting greeting: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/audio/session/end")
    async def end_audio_session(session_id: str):
        """
        End an audio conversation session.
        
        Generates a natural-language call summary (available via GET /api/v1/call-summary/{session_id}).
        Backend can fetch and store summaries for records.
        """
        try:
            # Acquire lock first to avoid TOCTOU: check and pop atomically under lock
            lock = _session_locks.setdefault(session_id, asyncio.Lock())
            async with lock:
                session_data = active_sessions.pop(session_id, None)
                if session_data is None:
                    raise HTTPException(status_code=404, detail="Session not found")
            # Do not pop lock: concurrent ops (e.g. WS update, another end) must use same lock.
            # Removing it would let a late setdefault create a new lock and break mutual exclusion.
            history = session_data.get("conversation_history", [])
            
            # Generate and store summary (TTL: 24h) - use fallback if generation fails
            try:
                summary = await _generate_call_summary(history, config)
            except Exception as ex:
                logger.warning(f"Could not generate summary for session {session_id}: {ex}")
                summary = "No conversation recorded." if not history else "Call completed."
            expires_at = datetime.utcnow() + timedelta(seconds=CALL_SUMMARY_TTL_SECONDS)
            async with _get_call_summaries_lock():
                call_summaries[session_id] = {"summary": summary, "expires_at": expires_at}
                _prune_expired_summaries()
            
            logger.info(f"Ended session {session_id}")
            duration_sec = (
                datetime.now() - datetime.fromisoformat(session_data["created_at"])
            ).total_seconds()
            if config.ENABLE_METRICS:
                quality_metrics.record_call_completion(
                    call_sid=session_id,
                    duration_seconds=duration_sec,
                    turn_count=session_data.get("turn_count", 0),
                )
            return {
                "session_id": session_id,
                "status": "ended",
                "turn_count": session_data["turn_count"],
                "duration_seconds": duration_sec,
                "conversation_history": history,
                "summary": summary
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/call-summary/{session_id}", response_class=Response)
    async def get_call_summary(session_id: str):
        """
        Get call summary as plain text.
        
        Summaries are generated when a session ends (POST /audio/session/end).
        Stored in-memory with 24h TTL; backend should fetch and persist as needed.
        """
        async with _get_call_summaries_lock():
            _prune_expired_summaries()
            entry = call_summaries.get(session_id)
            if not entry or entry.get("expires_at", datetime.max) <= datetime.utcnow():
                raise HTTPException(status_code=404, detail="Call summary not found or expired")
            summary_text = entry["summary"]
        return Response(
            content=summary_text,
            media_type="text/plain"
        )
    
    @app.get("/audio/session/{session_id}")
    async def get_session_status(session_id: str):
        """Get current session status and conversation history"""
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return active_sessions[session_id]
    
    @app.websocket("/audio/stream")
    async def audio_stream_handler(websocket: WebSocket):
        """
        Real-time audio streaming (generic WebSocket, vendor-agnostic)
        
        Send audio chunks, receive AI response audio chunks
        """
        await websocket.accept()
        session_id = None
        
        try:
            logger.info("Audio stream WebSocket connected")
            
            # Wait for initial session setup message
            setup_msg = await websocket.receive_json()
            business_id = setup_msg.get("business_id", "default")
            business_name = setup_msg.get("business_name")
            if not business_name or not str(business_name).strip():
                await websocket.send_json({
                    "type": "error",
                    "detail": "business_name is required for greeting (provision from onboarding)"
                })
                await websocket.close(code=4000)
                return
            business_name = str(business_name).strip()
            requested_session_id = setup_msg.get("session_id")
            customer_id = setup_msg.get("customer_id")
            conversation_id = setup_msg.get("conversation_id")
            call_type = setup_msg.get("call_type", "inbound")
            reason = setup_msg.get("reason")  # for outbound: abandoned_cart, order_issues, etc.
            # Reuse existing session if provided and found (e.g. created via POST /audio/session/start)
            # Hold session lock to avoid race: session/end could pop between read and update, causing re-insert leak
            if requested_session_id:
                lock = _session_locks.setdefault(requested_session_id, asyncio.Lock())
                async with lock:
                    if requested_session_id in active_sessions:
                        session_id = requested_session_id
                        # Do not overwrite customer_id, conversation_id, business_id on existing session:
                        # prevents mixing/misattribution when multiple WebSockets share the same session
                    else:
                        # Session doesn't exist: create new with client's requested ID (preserves session continuity)
                        session_id = requested_session_id
                        active_sessions[session_id] = {
                            "session_id": session_id,
                            "business_id": business_id,
                            "business_name": business_name,
                            "customer_id": customer_id,
                            "conversation_id": conversation_id,
                            "call_type": call_type,
                            "reason": reason,
                            "created_at": datetime.now().isoformat(),
                            "conversation_history": [],
                            "turn_count": 0
                        }
            else:
                session_id = requested_session_id or str(uuid.uuid4())
                active_sessions[session_id] = {
                    "session_id": session_id,
                    "business_id": business_id,
                    "business_name": business_name,
                    "customer_id": customer_id,
                    "conversation_id": conversation_id,
                    "call_type": call_type,
                    "reason": reason,
                    "created_at": datetime.now().isoformat(),
                    "conversation_history": [],
                    "turn_count": 0
                }
            
            await websocket.send_json({
                "type": "session_started",
                "session_id": session_id
            })
            # Introduction first: send greeting (text + audio) before any user audio
            greeting_text = get_greeting_text(
                call_type=call_type,
                business_name=business_name,
                reason=reason,
            )
            greeting_audio = await tts_service.synthesize_speech(
                text=greeting_text,
                output_format="MP3"
            )
            greeting_payload = {
                "type": "greeting",
                "call_type": call_type,
                "text": greeting_text,
            }
            if greeting_audio:
                greeting_payload["audio"] = base64.b64encode(greeting_audio).decode("utf-8")
            await websocket.send_json(greeting_payload)
            
            # Process audio stream
            while True:
                # Receive audio data
                message = await websocket.receive()
                
                if message["type"] == "websocket.disconnect":
                    break
                    
                if "bytes" in message:
                    # Process audio bytes
                    audio_data = message["bytes"]
                    t0 = time.perf_counter()
                    # Transcribe
                    transcript = await stt_service.transcribe_audio(audio_data)
                    
                    if transcript:
                        # Send transcript to client
                        await websocket.send_json({
                            "type": "transcript",
                            "text": transcript
                        })
                        
                        # Get AI response - include identity for shared memory
                        # Use session's business_id when reusing (avoids mixing conversation across businesses)
                        sess = active_sessions.get(session_id, {})
                        routing_business_id = sess.get("business_id", business_id)
                        context = {
                            "channel": "voice",
                            "session_id": session_id,
                            "business_id": routing_business_id,
                            "customer_id": sess.get("customer_id"),
                            "conversation_id": sess.get("conversation_id"),
                            "call_type": sess.get("call_type", "inbound"),
                        }
                        result = await agent_router.route_message(
                            call_id=session_id,
                            business_id=routing_business_id,
                            message=transcript,
                            context=context
                        )
                        ai_text = result.get("response", "") if result else ""
                        esc_required = result.get("escalation_required", False) if result else False
                        esc_payload = result.get("escalation") if result else None
                        ai_for_history = ai_text or "[Escalation requested]"
                        if esc_required:
                            await websocket.send_json({
                                "type": "escalation",
                                "payload": esc_payload
                            })
                        else:
                            response_text = ai_text or "I'm sorry, I'm having trouble processing that."
                            processed = prompt_processor.process_response(context, response_text)
                            ai_for_history = processed
                            await websocket.send_json({
                                "type": "ai_response",
                                "text": processed
                            })
                            response_audio = await tts_service.synthesize_speech(
                                text=processed,
                                output_format="MP3"
                            )
                            if response_audio:
                                await websocket.send_bytes(response_audio)
                        # Update session atomically
                        lock = _session_locks.setdefault(session_id, asyncio.Lock())
                        async with lock:
                            if session_id in active_sessions:
                                active_sessions[session_id]["turn_count"] += 1
                                active_sessions[session_id]["conversation_history"].append({
                                    "user": transcript,
                                    "ai": ai_for_history,
                                    "timestamp": datetime.now().isoformat()
                                })
                            if config.ENABLE_METRICS:
                                processing_time = time.perf_counter() - t0
                                turn_count_after = active_sessions.get(session_id, {}).get("turn_count", 1)
                                quality_metrics.record_turn(
                                    call_id=session_id,
                                    turn_count=turn_count_after,
                                    transcript_length=len(transcript or ""),
                                    processing_time=processing_time,
                                )
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session {session_id}")
        except Exception as e:
            logger.error(f"Error in audio stream: {str(e)}")
            await websocket.close(code=1011, reason=str(e))
        finally:
            # Cleanup session and generate summary for WebSocket-ended calls (always, even if empty)
            # Acquire lock before popping to avoid race with concurrent session updates (same pattern as end_audio_session)
            if session_id:
                lock = _session_locks.setdefault(session_id, asyncio.Lock())
                async with lock:
                    session_data = active_sessions.pop(session_id, None)
                # Do not pop lock: concurrent ops must use same lock; removing would break mutual exclusion.
                if session_data is not None:
                    if config.ENABLE_METRICS:
                        duration_sec = (
                            datetime.now() - datetime.fromisoformat(session_data["created_at"])
                        ).total_seconds()
                        quality_metrics.record_call_completion(
                            call_sid=session_id,
                            duration_seconds=duration_sec,
                            turn_count=session_data.get("turn_count", 0),
                        )
                    history = session_data.get("conversation_history", [])
                    try:
                        summary = await _generate_call_summary(history, config)
                    except Exception as ex:
                        logger.warning(f"Could not generate summary on WebSocket end: {ex}")
                        summary = "No conversation recorded." if not history else "Call completed."
                    expires_at = datetime.utcnow() + timedelta(seconds=CALL_SUMMARY_TTL_SECONDS)
                    async with _get_call_summaries_lock():
                        call_summaries[session_id] = {"summary": summary, "expires_at": expires_at}
                        _prune_expired_summaries()
    
    # ==================== VOICE TEST ENDPOINTS ====================
    
    class VoiceTestRequest(BaseModel):
        text: str
        format: Optional[str] = "MP3"  # MP3, WAV, or LINEAR16
    
    @app.post("/voice/test")
    async def test_voice_synthesis(request_body: VoiceTestRequest):
        """
        Test endpoint for voice synthesis
        
        Accepts text and returns audio file for testing the Nigerian English female voice.
        """
        try:
            if not request_body.text or len(request_body.text.strip()) == 0:
                raise HTTPException(status_code=400, detail="Text cannot be empty")
            
            if len(request_body.text) > 1000:
                raise HTTPException(status_code=400, detail="Text too long. Maximum 1000 characters.")
            
            # Synthesize speech
            audio_data = await tts_service.synthesize_speech(
                text=request_body.text,
                output_format=request_body.format
            )
            
            if not audio_data:
                raise HTTPException(status_code=500, detail="Failed to synthesize speech")
            
            # Determine content type
            format_lower = request_body.format.upper()
            content_types = {
                "MP3": "audio/mpeg",
                "WAV": "audio/wav",
                "LINEAR16": "audio/wav"
            }
            content_type = content_types.get(format_lower, "audio/mpeg")
            
            logger.info(f"Voice test: Synthesized '{request_body.text[:50]}...' in {format_lower} format")
            
            return Response(
                content=audio_data,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="voice_test.{format_lower.lower()}"'
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in voice test endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/voice/test/info")
    async def get_voice_info():
        """Get information about the current voice configuration"""
        try:
            voice_info = await tts_service.get_voice_characteristics()
            return {
                "status": "success",
                "current_voice": {
                    "voice_id": config.ELEVENLABS_VOICE_ID,
                    "provider": "ElevenLabs",
                    "description": "Nigerian English Female Voice"
                },
                "available_voices": voice_info.get("available_voices", []),
                "audio_settings": {
                    "sample_rate": config.AUDIO_SAMPLE_RATE,
                    "channels": config.AUDIO_CHANNELS
                }
            }
        except Exception as e:
            logger.error(f"Error getting voice info: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==================== WHISPER TEST ENDPOINTS ====================

    @app.post("/whisper/test")
    async def test_whisper_transcription(audio_file: UploadFile = File(...)):
        """
        Test endpoint for STT (Whisper)

        Upload an audio file (e.g. MP3, WAV, etc.) and get the transcription.
        Use this to verify the STT pipeline is working before testing the full voice flow.
        """
        try:
            audio_data = await audio_file.read()
            if not audio_data or len(audio_data) == 0:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            if len(audio_data) > 25 * 1024 * 1024:  # 25MB limit
                raise HTTPException(status_code=400, detail="File too large. Maximum 25MB.")
            transcript = await stt_service.transcribe_audio(audio_data)
            if transcript is None:
                raise HTTPException(
                    status_code=400,
                    detail="Could not transcribe audio (no speech detected)"
                )
            logger.info(f"Whisper test: {transcript}")
            return {
                "status": "success",
                "transcript": transcript,
                "filename": audio_file.filename or "audio",
                "size_bytes": len(audio_data),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in whisper test endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/whisper/test/info")
    async def get_whisper_info():
        """Get information about the current whisper configuration"""
        return {
            "status": "success",
            "stt": {
                "provider": "OpenAI",
                "model": "whisper-1",
                "description": "STT for voice pipeline",
                "sample_rate": config.STT_SAMPLE_RATE,
                "supported_input_formats": "MP3, WAV, WEBM, MULAW (converted internally)",
            },
        }

    @app.get("/metrics")
    async def get_metrics():
        """Get basic metrics"""
        if not config.ENABLE_METRICS:
            raise HTTPException(status_code=404, detail="Metrics disabled")

        return quality_metrics.get_metrics()

    return app