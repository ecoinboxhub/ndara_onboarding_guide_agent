"""
Agent Router - Routes voice messages to appropriate AI agents
"""

import logging
import asyncio
import httpx
from typing import Optional, Dict, Any
from ..config import VoiceConfig

logger = logging.getLogger(__name__)

class AgentRouter:
    """Route voice messages to Customer AI"""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self.customer_ai_client = httpx.AsyncClient(
            base_url=config.CUSTOMER_AI_BASE_URL,
            headers={"X-API-Key": config.CUSTOMER_AI_API_KEY},
            timeout=30.0
        )
    
    async def onboard_business(
        self,
        business_id: Optional[str],
        body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Onboard a business to Customer AI (same knowledge base used by voice and chat).
        Proxies to Customer AI POST /api/v1/onboard.
        """
        try:
            url = "/api/v1/onboard"
            if business_id:
                url = f"/api/v1/onboard?business_id={business_id}"
            response = await self.customer_ai_client.post(url, json=body)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Customer AI onboard error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error onboarding business: {str(e)}")
            raise
    
    async def route_message(
        self,
        call_id: str,
        business_id: Optional[str],
        message: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Route message to appropriate AI agent with feature access support

        Returns:
            Dict with keys: response (str), escalation_required (bool), escalation (dict|None)
            or None if routing failed
        """
        try:
            # Check for feature access requests during both inbound and outbound calls
            if context.get("call_type") in ["inbound", "outbound"]:
                feature_result = await self._handle_feature_access(
                    call_id=call_id,
                    business_id=business_id,
                    message=message,
                    context=context
                )
                if feature_result:
                    return feature_result

            # Determine routing based on call type
            routing_business_id = business_id or "default"
            return await self._route_to_customer_ai(
                call_id=call_id,
                business_id=routing_business_id,
                message=message,
                context=context
            )
        except Exception as e:
            logger.error(f"Error routing message for call {call_id}: {str(e)}")
            return None
    
    async def _route_to_customer_ai(
        self,
        call_id: str,
        business_id: str,
        message: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Route message to Customer AI

        Returns:
            Dict with response, escalation_required, escalation; or fallback dict on error
        """
        fallback = {
            "response": "I'm sorry, I'm having trouble processing your request. Please try again.",
            "escalation_required": False,
            "escalation": None,
        }
        try:
            payload = {
                "message": message,
                "customer_id": context.get("customer_id", f"call_{call_id}"),
                "context": {
                    "channel": "voice",
                    "call_id": call_id,
                    "conversation_id": context.get("conversation_id"),
                    "call_type": context.get("call_type"),
                    "persona": {
                        "agent_name": context.get("agent_name", "Assistant"),
                        "gender": "female",
                        "accent": "nigerian"
                    }
                }
            }
            response = await self.customer_ai_client.post(
                f"/api/v1/chat?business_id={business_id}",
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "response": data.get("response", ""),
                    "escalation_required": data.get("escalation_required", False),
                    "escalation": data.get("escalation"),
                }
            logger.error(f"Customer AI error: {response.status_code} - {response.text}")
            return fallback
        except httpx.TimeoutException:
            logger.error("Customer AI request timed out")
            fallback["response"] = "I'm sorry, the request is taking too long. Please try again."
            return fallback
        except Exception as e:
            logger.error(f"Error routing to Customer AI: {str(e)}")
            fallback["response"] = "I'm sorry, I'm experiencing technical difficulties. Please try again later."
            return fallback
    
    async def get_conversation_history(
        self,
        business_id: str,
        customer_id: str
    ) -> list:
        """
        Get conversation history for context
        
        Args:
            business_id: Business identifier
            customer_id: Customer identifier
            
        Returns:
            Conversation history
        """
        try:
            response = await self.customer_ai_client.get(
                f"/api/v1/conversation-history?business_id={business_id}&customer_id={customer_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("history", [])
            else:
                logger.warning(f"Could not fetch conversation history: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching conversation history: {str(e)}")
            return []
    
    async def update_conversation_context(
        self,
        call_id: str,
        business_id: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Update conversation context
        
        Args:
            call_id: Call identifier
            business_id: Business identifier
            context: Updated context
            
        Returns:
            Success status
        """
        try:
            payload = {
                "call_id": call_id,
                "business_id": business_id,
                "context": context
            }
            
            response = await self.customer_ai_client.post(
                f"/api/v1/update-context?business_id={business_id}",
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error updating conversation context: {str(e)}")
            return False
    
    async def _handle_feature_access(
        self,
        call_id: str,
        business_id: Optional[str],
        message: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle feature access requests during outbound calls
        """
        try:
            feature_requests = self._detect_feature_requests(message)
            if not feature_requests:
                return None
            routing_business_id = business_id or "default"
            enhanced_context = {
                **context,
                "feature_access": True,
                "requested_features": feature_requests,
                "call_type": "outbound_with_features"
            }
            result = await self._route_to_customer_ai(
                call_id=call_id,
                business_id=routing_business_id,
                message=message,
                context=enhanced_context
            )
            if result:
                feature_confirmation = self._generate_feature_confirmation(feature_requests)
                result["response"] = f"{result.get('response', '')} {feature_confirmation}".strip()
                return result
            return None
        except Exception as e:
            logger.error(f"Error handling feature access for call {call_id}: {str(e)}")
            return None
    
    def _detect_feature_requests(self, message: str) -> list:
        """Detect feature requests in customer message"""
        feature_keywords = {
            "appointment": ["appointment", "book", "schedule", "booking", "reservation", "meeting", "consultation"],
            "order_tracking": ["track", "order", "delivery", "status", "where is my", "shipping", "package"],
            "account": ["account", "profile", "update", "change", "information", "details", "settings"],
            "payment": ["payment", "pay", "billing", "invoice", "charge", "bill", "money", "cost"],
            "service": ["service", "help", "support", "assistance", "problem", "issue", "trouble", "fix"],
            "cancellation": ["cancel", "stop", "end", "terminate", "discontinue", "remove"],
            "refund": ["refund", "return", "money back", "reimburse", "credit"],
            "rescheduling": ["reschedule", "change time", "move", "postpone", "different time"],
            "information": ["hours", "location", "address", "phone", "contact", "directions"],
            "pricing": ["price", "cost", "fee", "charge", "how much", "quote", "estimate"]
        }
        
        detected_features = []
        message_lower = message.lower()
        
        for feature, keywords in feature_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_features.append(feature)
        
        return detected_features
    
    def _generate_feature_confirmation(self, features: list) -> str:
        """Generate confirmation message for feature access"""
        if not features:
            return ""
        
        feature_names = {
            "appointment": "appointment booking",
            "order_tracking": "order tracking",
            "account": "account management",
            "payment": "payment processing",
            "service": "service support",
            "cancellation": "cancellation assistance",
            "refund": "refund processing",
            "rescheduling": "rescheduling assistance",
            "information": "information services",
            "pricing": "pricing information"
        }
        
        if len(features) == 1:
            feature_name = feature_names.get(features[0], features[0])
            return f"I can help you with {feature_name} right now."
        else:
            feature_list = [feature_names.get(f, f) for f in features]
            return f"I can help you with {', '.join(feature_list)} right now."
    
    async def close(self):
        """Close HTTP clients"""
        try:
            await self.customer_ai_client.aclose()
        except Exception as e:
            logger.error(f"Error closing HTTP clients: {str(e)}")

