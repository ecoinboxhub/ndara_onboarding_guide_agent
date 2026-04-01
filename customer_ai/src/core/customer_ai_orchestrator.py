"""
Customer AI Orchestrator
Routes messages through the LangGraph agent (tool-calling loop).
Keeps onboarding, escalation, feedback, and model management unchanged.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

import os

from .industry_classifier import IndustryClassifier
from .business_specific_ai import BusinessSpecificAI
from .conversation_manager import ConversationManager
from .model_registry import get_model_registry
from .finetuning_manager import get_finetuning_manager
from .knowledge_base import get_knowledge_base
from .vector_store import get_vector_store
from .payment_handler import get_payment_handler
from .customer_agent import build_agent_graph, invoke_agent

logger = logging.getLogger(__name__)


def _scope_key(prefix: str, value: Optional[str]) -> Optional[str]:
    """Return scope key; avoid double-prefixing when value already has prefix (e.g. cust_123, conv_456).
    Uses case-insensitive prefix matching only; preserves original casing to avoid merging distinct IDs."""
    if not value:
        return None
    s = str(value)
    if s.lower().startswith(prefix.lower()):
        return s
    return f"{prefix}{s}"


class CustomerAIOrchestrator:
    """
    Main orchestrator for Customer AI system - AI Engineering focused
    """
    
    def __init__(self):
        # Initialize AI components only
        self.industry_classifier = IndustryClassifier()
        
        # Business-specific AI instances (kept for onboarding data, FAQs, etc.)
        self.business_ais = {}

        # Compiled LangGraph agents per business (built on first chat after onboarding)
        self.agent_graphs = {}
        
        # Conversation managers per business:scope (capped to avoid unbounded memory growth)
        self.conversation_managers = {}
        # Tracks last-access time per manager key for LRU eviction
        self._conversation_manager_last_used: Dict[str, datetime] = {}
        try:
            self._conversation_manager_cap = int(os.getenv("CONVERSATION_MANAGER_CAP", "500"))
        except (TypeError, ValueError):
            self._conversation_manager_cap = 500
        
        # RAG components
        self.knowledge_base = get_knowledge_base()
        self.vector_store = get_vector_store()
        
        # Model registry and fine-tuning
        self.model_registry = get_model_registry()
        # Fine-tuning is archived for later use and disabled by default.
        # Enable explicitly via environment variable to avoid implying it's active in production.
        self.finetuning_manager = None
        if os.getenv("ENABLE_FINETUNING", "").strip().lower() in ("1", "true", "yes", "on"):
            try:
                self.finetuning_manager = get_finetuning_manager()
            except ValueError:
                self.finetuning_manager = None
                logger.warning("Fine-tuning manager not initialized (no OpenAI API key)")
        
        logger.info("Customer AI Orchestrator initialized (LangGraph)")
    
    def onboard_business(self, business_id: str, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Onboard a new business and train their AI
        """
        try:
            # Step 1: Classify industry
            classification_result = self.industry_classifier.classify_business(business_data)
            
            if not classification_result['success']:
                return {
                    'success': False,
                    'error': f"Industry classification failed: {classification_result.get('error')}"
                }
            
            industry = classification_result['industry']
            confidence = classification_result['confidence']
            
            # Step 2: Validate data against industry requirements
            validation_result = self.industry_classifier.validate_industry_data(industry, business_data)
            
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': f"Data validation failed: {validation_result['errors']}",
                    'validation_result': validation_result
                }
            
            # Step 3: Create business-specific AI
            business_ai = BusinessSpecificAI(business_id, industry)
            
            # Check for fine-tuned model (industry-level or business-specific)
            model_info = self.model_registry.get_model_for_request(business_id, industry)
            if model_info['type'] != 'base_model':
                business_ai.fine_tuned_model = model_info['model_id']
                logger.info(f"Using {model_info['type']} model: {model_info['model_id']}")
            
            # Step 4: Train AI with business data (includes RAG indexing)
            training_result = business_ai.train_with_business_data(business_data)
            
            if not training_result['success']:
                return {
                    'success': False,
                    'error': f"AI training failed: {training_result.get('error')}"
                }
            
            # Step 5: Store business AI instance
            self.business_ais[business_id] = business_ai
            
            # Step 6: Create default conversation manager for this business (with industry for escalation)
            # Per-customer/per-conversation managers are created lazily in process_customer_message
            default_key = f"{business_id}:default"
            conversation_manager = ConversationManager(business_id, industry=industry)
            self.conversation_managers[default_key] = conversation_manager
            
            return {
                'success': True,
                'business_id': business_id,
                'industry': industry,
                'confidence': confidence,
                'training_result': training_result,
                'validation_result': validation_result,
                'conversation_manager': True,
                'model_info': model_info
            }
            
        except Exception as e:
            logger.error(f"Error onboarding business {business_id}: {str(e)}")
            return {
                'success': False,
                'error': f"Error onboarding business: {str(e)}"
            }
    
    # ── LangGraph agent lifecycle ──────────────────────────────────────────

    def _get_or_build_graph(self, business_id: str):
        """Lazily compile and cache a LangGraph agent for a business.

        Returns (compiled_graph, product_media_ref) or None if business not found.
        product_media_ref is the mutable list that product_search writes to.
        """
        if business_id in self.agent_graphs:
            return self.agent_graphs[business_id]

        business_ai = self.business_ais.get(business_id)
        if not business_ai:
            return None

        payment_handler = get_payment_handler(business_id)

        compiled_graph, product_media_ref = build_agent_graph(
            business_id=business_id,
            business_data=business_ai.business_data,
            industry=business_ai.industry,
            knowledge_base=self.knowledge_base,
            payment_handler=payment_handler,
            model_name=business_ai.fine_tuned_model or business_ai.model_name,
        )
        self.agent_graphs[business_id] = (compiled_graph, product_media_ref)
        logger.info(f"LangGraph agent compiled for business {business_id}")
        return compiled_graph, product_media_ref

    # ── Main chat entry point ───────────────────────────────────────────

    def process_customer_message(
        self, 
        business_id: str, 
        customer_message: str, 
        customer_id: str = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process customer message via the LangGraph agent and return AI response.
        """
        try:
            business_id = str(business_id)
            context = context or {}

            # Check if business AI exists
            if business_id not in self.business_ais:
                try:
                    stats = self.knowledge_base.get_knowledge_stats(business_id)
                    has_knowledge_base = stats is not None
                except Exception:
                    has_knowledge_base = False

                available_ids = list(self.business_ais.keys())
                logger.warning(
                    f"Business AI not found for business_id: {business_id}. "
                    f"Available: {available_ids}. KB exists: {has_knowledge_base}"
                )
                if has_knowledge_base:
                    error_msg = (
                        f"Business AI instance lost (server restart?). "
                        f"Re-onboard via POST /api/v1/onboard?business_id={business_id}"
                    )
                else:
                    error_msg = (
                        f"Business not onboarded. "
                        f"POST /api/v1/onboard?business_id={business_id} first."
                    )
                return {"success": False, "error": error_msg}

            business_ai = self.business_ais[business_id]

            # ── Compile (or reuse) LangGraph agent ───────────────────────
            graph_result = self._get_or_build_graph(business_id)
            if not graph_result:
                return {"success": False, "error": "Failed to compile agent graph."}
            compiled_graph, product_media_ref = graph_result

            # ── Conversation manager for escalation tracking ─────────────
            scope_key = "default"
            if context:
                conv_val = _scope_key("conv_", context.get("conversation_id"))
                if conv_val:
                    scope_key = conv_val
                else:
                    cust_val = _scope_key("cust_", context.get("customer_id"))
                    if cust_val:
                        scope_key = cust_val
            if scope_key == "default" and customer_id:
                cust_val = _scope_key("cust_", customer_id)
                if cust_val:
                    scope_key = cust_val
            manager_key = f"{business_id}:{scope_key}"
            conversation_manager = self.conversation_managers.get(manager_key)
            # Update LRU access time whenever we touch a manager
            self._conversation_manager_last_used[manager_key] = datetime.now()

            if not conversation_manager:
                # Evict least-recently-used managers when at cap
                if len(self.conversation_managers) >= self._conversation_manager_cap:
                    target_size = max(1, int(self._conversation_manager_cap * 0.8))
                    excess = len(self.conversation_managers) - target_size
                    # Sort by last-used time ascending (oldest first)
                    lru_keys = sorted(
                        self._conversation_manager_last_used,
                        key=lambda k: self._conversation_manager_last_used[k]
                    )[:excess]
                    for k in lru_keys:
                        self.conversation_managers.pop(k, None)
                        self._conversation_manager_last_used.pop(k, None)
                    logger.debug(f"LRU evicted {len(lru_keys)} conversation managers (cap={self._conversation_manager_cap})")
                conversation_manager = ConversationManager(business_id, industry=business_ai.industry)
                self.conversation_managers[manager_key] = conversation_manager

            # ── Normalise backend conversation_history ────────────────────
            backend_history = context.get("conversation_history") or context.get("recent_turns") or []
            if not isinstance(backend_history, list):
                backend_history = []
            conversation_history = []
            for t in backend_history:
                if isinstance(t, dict):
                    conversation_history.append({
                        "role": t.get("role", "customer"),
                        "message": t.get("message") or t.get("content", ""),
                    })
                else:
                    conversation_history.append({
                        "role": getattr(t, "role", "customer"),
                        "message": getattr(t, "message", "") or getattr(t, "content", ""),
                    })

            # ── Greeting mode ────────────────────────────────────────────
            is_first_interaction = context.get("is_first_interaction") is True
            is_new_day = context.get("is_new_day") is True
            turn_count = len(conversation_history)

            if is_first_interaction:
                greeting_mode = "introduction"
            elif is_new_day or turn_count == 0:
                greeting_mode = "day_greeting"
            else:
                greeting_mode = "none"

            current_hour = datetime.now().hour
            if current_hour < 12:
                time_of_day = "morning"
            elif current_hour < 17:
                time_of_day = "afternoon"
            else:
                time_of_day = "evening"

            # ── Business name ────────────────────────────────────────────
            profile = business_ai.business_data.get("business_profile", {})
            business_name = (
                profile.get("business_name")
                or business_ai.business_data.get("name", "our business")
            )

            # ── Invoke LangGraph agent ───────────────────────────────────
            # Resolve personality from business ai_settings (falls back to nigerian_business)
            _ai_settings = business_ai.business_data.get("ai_settings") or {}
            if isinstance(_ai_settings, dict):
                _personality = _ai_settings.get("personality") or "nigerian_business"
            else:
                _personality = "nigerian_business"

            agent_response = invoke_agent(
                compiled_graph=compiled_graph,
                customer_message=customer_message,
                conversation_history=conversation_history,
                business_name=business_name,
                business_id=business_id,
                industry=business_ai.industry,
                customer_id=customer_id or "",
                channel=context.get("channel", "whatsapp"),
                greeting_mode=greeting_mode,
                time_of_day=time_of_day,
                personality=_personality,
                product_media_ref=product_media_ref,
            )

            # ── Build response dict (backward-compatible with old API) ───
            response: Dict[str, Any] = agent_response.model_dump()

            # ── Update conversation manager for escalation tracking ──────
            if conversation_manager and agent_response.success:
                score_map = {"negative": -0.7, "positive": 0.7}
                sentiment_score = score_map.get(agent_response.sentiment, 0.0)
                customer_metadata = {
                    "sentiment": {"sentiment": agent_response.sentiment, "score": sentiment_score},
                    "intent": {"intent": agent_response.intent},
                }
                conversation_manager.add_turn("customer", customer_message, metadata=customer_metadata)
                conversation_manager.add_turn("ai", agent_response.response)

                response["conversation_analytics"] = conversation_manager.get_conversation_analytics()

                escalation_payload = conversation_manager.get_escalation_payload()
                if escalation_payload["escalation_required"]:
                    response["escalation_required"] = True
                    response["escalation"] = escalation_payload["escalation"]

            return response

        except Exception as e:
            logger.error(f"Error processing customer message: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Error processing customer message: {str(e)}",
            }
    
    def extract_intent(self, business_id: str, message: str) -> Dict[str, Any]:
        """
        Extract intent from customer message (for backend team)
        """
        try:
            if business_id not in self.business_ais:
                return {
                    'success': False,
                    'error': f"Business AI not found for business_id: {business_id}"
                }
            
            business_ai = self.business_ais[business_id]
            intent_result = business_ai._analyze_intent(message)
            
            return {
                'success': True,
                'intent': intent_result.get('intent'),
                'confidence': intent_result.get('confidence'),
                'entities': intent_result.get('entities', {}),
                'metadata': intent_result.get('metadata', {})
            }
            
        except Exception as e:
            logger.error(f"Error extracting intent: {str(e)}")
            return {
                'success': False,
                'error': f"Error extracting intent: {str(e)}"
            }
    
    def analyze_sentiment(self, business_id: str, message: str) -> Dict[str, Any]:
        """
        Analyze sentiment of customer message
        """
        try:
            if business_id not in self.business_ais:
                return {
                    'success': False,
                    'error': f"Business AI not found for business_id: {business_id}"
                }
            
            business_ai = self.business_ais[business_id]
            sentiment_result = business_ai._analyze_sentiment(message)
            
            return {
                'success': True,
                'sentiment': sentiment_result.get('sentiment'),
                'score': sentiment_result.get('score'),
                'confidence': sentiment_result.get('confidence')
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                'success': False,
                'error': f"Error analyzing sentiment: {str(e)}"
            }
    
    def process_feedback(self, business_id: str, customer_id: Optional[str], rating: int, feedback_text: str = None, conversation_id: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process customer feedback for AI learning
        """
        try:
            if business_id not in self.business_ais:
                return {
                    'success': False,
                    'error': f"Business AI not found for business_id: {business_id}"
                }
            # Same scoping logic as process_customer_message: context first; fall back to params if context lacks scope
            scope_key = "default"
            if context is not None:
                conv_val = _scope_key("conv_", context.get("conversation_id"))
                if conv_val:
                    scope_key = conv_val
                else:
                    cust_val = _scope_key("cust_", context.get("customer_id"))
                    if cust_val:
                        scope_key = cust_val
            if scope_key == "default":
                conv_val = _scope_key("conv_", conversation_id)
                if conv_val:
                    scope_key = conv_val
                else:
                    cust_val = _scope_key("cust_", customer_id)
                    if cust_val:
                        scope_key = cust_val
            manager_key = f"{business_id}:{scope_key}"
            conversation_manager = self.conversation_managers.get(manager_key)
            if not conversation_manager:
                business_ai = self.business_ais[business_id]
                conversation_manager = ConversationManager(business_id, industry=business_ai.industry)
                self.conversation_managers[manager_key] = conversation_manager
            
            # Store feedback for learning
            outcome = {
                'rating': rating,
                'feedback_text': feedback_text,
                'customer_id': customer_id,
                'timestamp': datetime.now().isoformat()
            }
            
            learning_result = conversation_manager.learn_from_conversation(outcome)
            
            return {
                'success': True,
                'learning_result': learning_result,
                'message': 'Feedback processed for AI learning'
            }
            
        except Exception as e:
            logger.error(f"Error processing feedback: {str(e)}")
            return {
                'success': False,
                'error': f"Error processing feedback: {str(e)}"
            }
    
    def get_model_status(self, business_id: str) -> Dict[str, Any]:
        """
        Get AI model status for a business
        """
        try:
            if business_id not in self.business_ais:
                return {
                    'success': False,
                    'error': f"Business AI not found for business_id: {business_id}"
                }
            
            business_ai = self.business_ais[business_id]
            model_info = self.model_registry.get_model_for_request(business_id, business_ai.industry)
            
            return {
                'success': True,
                'business_id': business_id,
                'industry': business_ai.industry,
                'model_type': model_info['type'],
                'model_id': model_info['model_id'],
                'base_model': model_info.get('base_model'),
                'data_completeness': business_ai._calculate_data_completeness(),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting model status: {str(e)}")
            return {
                'success': False,
                'error': f"Error getting model status: {str(e)}"
            }
    
    def update_business_data(self, business_id: str, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update business data and retrain AI
        """
        try:
            if business_id not in self.business_ais:
                return {
                    'success': False,
                    'error': f"Business AI not found for business_id: {business_id}"
                }
            
            business_ai = self.business_ais[business_id]
            
            # Update business data (normalizes internally)
            update_result = business_ai.update_business_data(new_data)
            
            # Re-index in vector store with normalized data
            if update_result.get('success'):
                self.knowledge_base.index_business_data(business_id, business_ai.business_data)
                # Invalidate cached LangGraph agent so it rebuilds with updated data
                self.agent_graphs.pop(business_id, None)
            
            return update_result
            
        except Exception as e:
            logger.error(f"Error updating business data: {str(e)}")
            return {
                'success': False,
                'error': f"Error updating business data: {str(e)}"
            }
    
    def register_escalation(
        self,
        business_id: str,
        conversation_id: str,
        customer_id: str,
        reason: str,
        severity: str,
        context_summary: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        customer_message: Optional[str] = None,
        ai_response: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register an escalation to human/business owner.
        Backend calls this after detecting escalation_required in chat response.
        AI returns recommended_action; backend owns routing and notifications.
        """
        try:
            business_id = str(business_id)
            escalation_id = f"esc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{business_id[:8]}"

            # Get industry-specific recommended action if business exists
            recommended_action = "Connect with customer relations manager within 1 hour"
            if business_id in self.business_ais:
                try:
                    from ..domain.industries.config import get_escalation_recommendation
                    action = get_escalation_recommendation(
                        self.business_ais[business_id].industry, severity
                    )
                    if action:
                        recommended_action = action
                except ImportError:
                    pass

            # Build context for human agent
            context_for_agent = context_summary
            if conversation_history:
                context_for_agent += "\n\nConversation excerpt:"
                for turn in conversation_history[-6:]:  # Last 6 turns
                    role = turn.get("role", "unknown")
                    msg = turn.get("message", turn.get("content", ""))
                    context_for_agent += f"\n{role}: {msg[:200]}..."

            logger.info(
                f"Escalation registered: {escalation_id} business_id={business_id} "
                f"reason={reason} severity={severity}"
            )

            return {
                "success": True,
                "escalation_id": escalation_id,
                "recommended_action": recommended_action,
                "context_for_agent": context_for_agent,
            }
        except Exception as e:
            logger.error(f"Error registering escalation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status and health
        """
        try:
            return {
                'success': True,
                'status': 'healthy',
                'components': {
                    'industry_classifier': True,
                    'conversation_manager': True,
                    'knowledge_base': True,
                    'vector_store': True,
                    'model_registry': True,
                    'finetuning_manager': self.finetuning_manager is not None
                },
                'business_count': len(self.business_ais),
                'active_conversations': len(self.conversation_managers)
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {
                'success': False,
                'error': f"Error getting system status: {str(e)}"
            }


# Singleton instance
_orchestrator_instance = None

def get_orchestrator() -> CustomerAIOrchestrator:
    """Get or create the singleton CustomerAIOrchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = CustomerAIOrchestrator()
    return _orchestrator_instance
