import os
import json
import logging
import asyncio
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta
from dotenv import load_dotenv

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

try:
    import openai
    from openai import APIError, AsyncOpenAI, RateLimitError, APITimeoutError
except ImportError:
    openai = None
    AsyncOpenAI = None
    APIError = Exception
    RateLimitError = Exception
    APITimeoutError = Exception

try:
    from .rag_manager import RAGManager
except ImportError:
    from rag_manager import RAGManager

from sqlalchemy.future import select
try:
    from .database import get_db, FailureLog, Escalation, AsyncSessionLocal
except ImportError:
    from database import get_db, FailureLog, Escalation, AsyncSessionLocal

logger = logging.getLogger(__name__)

load_dotenv()

ONBOARDING_SYSTEM_PROMPT = """You are the Ndara.ai Onboarding Guide, a highly intuitive and specialized AI assistant.
Your absolute goal is to help African B2B businesses and creators effortlessly set up their accounts without getting stuck.

You must speak in a friendly, conversational, and human-like voice. Use everyday English, and you may sprinkle in light Pidgin-style colloquialisms if appropriate.

The user is currently going through the Ndara.ai 7-Step Onboarding Process:
Step 1: Welcome & Basic Details (Business Name)
Step 2: WhatsApp Verification (OTP)
Step 3: Industry Selection
Step 4: Feature Mapping (Lead Management, Invoicing, etc.)
Step 5: Paywall / Free Trial Selection
Step 6: Dashboard Access & Walkthrough
Step 7: Business Data Upload for AI Training

INSTRUCTIONS:
1. Actively maintain the context of the user's business from the conversation history (e.g., if they say their business is "Eco Hub", remember that).
2. Guide them smoothly toward the next immediate step. If they are on Step 1, get their business name, then organically invite them to Step 2 (WhatsApp Verification).
3. If they ask a question, answer it clearly using the "SYSTEM RAG CONTEXT" provided to you for that specific turn.
4. Keep your responses concise (under 3 sentences usually) so it feels like a fast-paced chat.
5. Empathize and be encouraging!

If the user is stuck or frustrated (e.g. failing OTP repeatedly), output `[ESCALATE]` anywhere in your response so the system can gracefully transfer them to a human agent on the Admin Dashboard.
"""

def log_retry_attempt(retry_state):
    logger.warning(f"Retrying LLM API Call: attempt {retry_state.attempt_number} after error: {retry_state.outcome.exception()}")

class OnboardingGuideAgent:
    def __init__(self, faq_path: str = 'platform_onboarding_faq.json', db_path: str = "./vectordb", llm_provider: str = 'openai'):
        self.faq_path = faq_path
        self.llm_provider = llm_provider.lower()
        
        self.rag = RAGManager(db_path=db_path)
        self.rag.load_faq_into_db(self.faq_path)
        
        self.conversation_histories: Dict[str, List[Dict[str, str]]] = {}
        self.api_key = self._get_api_key(self.llm_provider)
        
        self.client = None
        if self.llm_provider == 'openai' and AsyncOpenAI:
            self.client = AsyncOpenAI(api_key=self.api_key)
            self.model_name = "gpt-4o-mini" # Using OpenAI cheap model for fallback scaling
            
        # Circuit Breaker state
        self._consecutive_failures = 0
        self._circuit_breaker_until = None
        
    def _get_api_key(self, provider: str) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((APIError, RateLimitError, APITimeoutError)),
        before_sleep=log_retry_attempt
    )
    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Centralized external API caller with Circuit Breakers."""
        if self._circuit_breaker_until and datetime.utcnow() < self._circuit_breaker_until:
            return "Circuit Breaker Active: System temporarily unavailable. Please try again soon."
            
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=400
            )
            self._consecutive_failures = 0 # Reset circuit breaker
            return response.choices[0].message.content
        except Exception as e:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 3:
                # Disable for 60 seconds
                self._circuit_breaker_until = datetime.utcnow() + timedelta(seconds=60)
                logger.error("CIRCUIT BREAKER ACTIVATED: LLM API failing repeatedly. Disabled for 60 seconds.")
            raise e

    async def _handle_state_machine(self, user_id: str, session_id: str, step: int, escalation_detected: bool = False):
        """Monitors failure rate and triggers live escalation logic via SQLite context."""
        async with AsyncSessionLocal() as db:
            q = await db.execute(select(FailureLog).where(FailureLog.user_id == user_id, FailureLog.step == step))
            failure_log = q.scalars().first()
            
            should_escalate = escalation_detected
            
            if not failure_log:
                failure_log = FailureLog(user_id=user_id, session_id=session_id, step=step, attempt_count=0)
                db.add(failure_log)
                
            # Treat each message at the exact same step conceptually as a failure/attempt progression
            failure_log.attempt_count += 1
            failure_log.last_attempt_at = datetime.utcnow()
            
            if failure_log.attempt_count >= 3:
                should_escalate = True
                
            if should_escalate:
                esc_q = await db.execute(select(Escalation).where(Escalation.user_id == user_id, Escalation.status == "pending"))
                existing_esc = esc_q.scalars().first()
                if not existing_esc:
                    from uuid import uuid4
                    new_esc = Escalation(
                        id=str(uuid4()),
                        user_id=user_id,
                        session_id=session_id,
                        step=step,
                        reason="max_attempts_reached" if failure_log.attempt_count >= 3 else "ai_flagged"
                    )
                    db.add(new_esc)
                    # Real-time WebSocket/Email mock logic
                    logger.critical(f"REAL-TIME ALERT: Escalation triggered for user {user_id} at step {step}. E-mailing admins (olusegun/segun). WebSocket pushed to Dashboard.")
                
            await db.commit()
            return should_escalate

    async def _log_transcript(self, user_id: str, session_id: str, role: str, content: str):
        # Transcripts conceptually exist in self.conversation_histories natively for now.
        pass

    async def process_message(self, user_id: str, current_step: int, user_message: str, session_id: str = "default_session") -> Tuple[str, Dict[str, Any]]:
        if not self.client:
            return "System Error: Missing LLM library or async capability.", {}
            
        # Check database State to see if admin has locked the chat
        async with AsyncSessionLocal() as db:
            esc_q = await db.execute(select(Escalation).where(Escalation.user_id == user_id, Escalation.status.in_(["pending", "in_progress", "accepted"])))
            active_esc = esc_q.scalars().first()
            if active_esc:
                return "Your request has been prioritized and a human support hero is actively checking your ticket right now. Please hold on!", {"escalate_to": "live_agent_bridge", "locked": True}
                
        # Continious Learning injection (Requirements 2.2 D)
        rag_context = self.rag.search_faq(user_message, n_results=1)
        similar_resolutions = self.rag.search_similar_resolutions(query=user_message, step_id=str(current_step), limit=2)
        
        few_shot_injection = ""
        if similar_resolutions:
            few_shot_injection = "\n--- PAST SUCCESSFUL RESOLUTIONS ---\n"
            for res in similar_resolutions:
                few_shot_injection += f"Similar Resolution Strategy: {res.get('full_text')}\n\n"
            few_shot_injection += "Use the above successful experiences as direct inspiration for your answer.\n"

        if user_id not in self.conversation_histories:
            self.conversation_histories[user_id] = [
                {"role": "system", "content": ONBOARDING_SYSTEM_PROMPT}
            ]
            
        turn_directive = (
            f"\n\n--- INTERNAL SYSTEM METADATA ENFORCER ---\n"
            f"The user is on step: {current_step}\n"
            f"SYSTEM RAG FAQ: {rag_context}\n"
            f"{few_shot_injection}"
            f"INSTRUCTION: Incorporate RAG answers cleanly without mentioning 'RAG' or 'internal docs'."
        )
        
        injected_user_message = f"User said: {user_message}{turn_directive}"
        self.conversation_histories[user_id].append({"role": "user", "content": injected_user_message})

        try:
            ai_message = await self._call_llm(messages=self.conversation_histories[user_id])
        except Exception as e:
            logger.error(f"Ultimate Fallback after Retries Failed: {e}")
            ai_message = "I am unfortunately experiencing critical technical network issues right now. Escalating your ticket natively."

        metadata = {"escalate_to": None}
        escalation_triggered = False
        
        if "[ESCALATE]" in ai_message or "critical technical network issues" in ai_message:
            ai_message = ai_message.replace("[ESCALATE]", "").strip()
            ai_message += "\n\nI'm transferring you to a live support hero right now to help clear this up."
            escalation_triggered = True
            
        # Execute State Machine Validations
        escalated_by_state = await self._handle_state_machine(user_id, session_id, current_step, escalation_triggered)
        if escalated_by_state:
            metadata["escalate_to"] = "live_agent_bridge"
            if not escalation_triggered:
                 ai_message += "\n\n(System Note: Our systems noticed you might be having difficulty. A live support agent has been notified and will jump in shortly.)"

        self.conversation_histories[user_id].append({"role": "assistant", "content": ai_message})
        
        return ai_message, metadata

