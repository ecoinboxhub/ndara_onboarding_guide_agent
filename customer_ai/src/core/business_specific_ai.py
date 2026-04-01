"""
Business-Specific AI Engine (data holder + onboarding utilities).

Main chat flow: LangGraph agent (customer_agent.py) handles all response generation.
This module provides:
  - train_with_business_data / update_business_data  (onboarding; used by orchestrator)
  - _calculate_data_completeness  (model status)

Legacy / standalone only (not used in the main chat or onboarding pipeline):
  - generate_ai_context_from_minimal_data  (AI-generated context; removed from onboarding to save tokens)
  - _analyze_intent / _analyze_sentiment  (used only by /extract-intent and /analyze-sentiment API endpoints)
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional

from .knowledge_base import get_knowledge_base

logger = logging.getLogger(__name__)


class BusinessSpecificAI:
    """
    Business-specific AI engine — stores onboarded business data and
    exposes helper utilities consumed by the orchestrator and API.
    """
    
    def __init__(self, business_id: str, industry: str):
        self.business_id = business_id
        self.industry = industry
        self.business_data: Dict[str, Any] = {}

        # RAG system
        self.knowledge_base = get_knowledge_base()
        
        # OpenAI setup
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("No OpenAI API key — using fallback responses")
        
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.lightweight_model = os.getenv("OPENAI_LIGHTWEIGHT_MODEL", "gpt-3.5-turbo")
        self.fine_tuned_model: Optional[str] = None
        self._openai_client = None

    def _get_openai_client(self):
        """Lazily create and reuse a single OpenAI client instance."""
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.openai_api_key)
        return self._openai_client

    # ── Data normalisation helpers ─────────────────────────────────────
    
    def _normalize_business_data(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize business data from new knowledge_data format to internal format.
        Supports both new knowledge_data structure and legacy business_data structure.
        """
        if "business_profile" in business_data:
            return business_data
        
        normalized = {
            "business_profile": {
                "business_name": business_data.get("business_info", {}).get("name", ""),
                "description": business_data.get("business_info", {}).get("description", ""),
                "industry": self.industry,
                "contact_info": {
                    "phone": business_data.get("business_info", {}).get("phone", ""),
                    "email": business_data.get("business_info", {}).get("email", ""),
                    "address": business_data.get("business_info", {}).get("address", ""),
                    "whatsapp_number": business_data.get("business_info", {}).get("whatsapp_number", ""),
                },
                "timezone": business_data.get("business_info", {}).get("timezone", "Africa/Lagos"),
            },
            "products_services": [],  # Catalog from backend AI Tools (product_search, get_product_by_id), not onboarding
            "faqs": business_data.get("faqs", []),
            "policies": business_data.get("policies", {}),
            "shipping_info": business_data.get("shipping_info", {}),
            "payment_details": business_data.get("payment_details", {}),
            "business_hours": business_data.get("business_hours", {}),
            "ai_enabled": business_data.get("ai_enabled", True),
            "collection_name": business_data.get("collection_name"),
            "ai_settings": business_data.get("ai_settings", {}),
            "_original_structure": "knowledge_data" if "business_info" in business_data else "legacy",
            "_original_data": business_data,
        }
        return normalized
    
    def _get_business_name(self) -> str:
        if not self.business_data:
            return "our business"
        return self.business_data.get("business_profile", {}).get("business_name", "our business")
    
    def _get_business_description(self) -> str:
        if not self.business_data:
            return ""
        return self.business_data.get("business_profile", {}).get("description", "")
    
    def _get_products_services(self) -> List[Dict[str, Any]]:
        if not self.business_data:
            return []
        return self.business_data.get("products_services", [])
    
    def _get_contact_info(self) -> Dict[str, Any]:
        if not self.business_data:
            return {}
        return self.business_data.get("business_profile", {}).get("contact_info", {})
    
    def _get_business_hours(self) -> Dict[str, Any]:
        if not self.business_data:
            return {}
        return self.business_data.get("business_hours", {})
    
    def _get_ai_settings(self) -> Dict[str, Any]:
        if not self.business_data:
            return {}
        return self.business_data.get("ai_settings", {})

    # ── Onboarding / training ──────────────────────────────────────────
    
    def train_with_business_data(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """Train AI with business-specific data and index for RAG."""
        try:
            self.business_data = self._normalize_business_data(business_data)
            
            indexing_result = {"success": False, "documents_indexed": 0}
            try:
                indexing_result = self.knowledge_base.index_business_data(
                    business_id=self.business_id,
                    business_data=self.business_data,
                )
                logger.info(f"Indexed {indexing_result.get('documents_indexed', 0)} documents for RAG")
            except Exception as rag_error:
                logger.warning(f"RAG indexing failed, continuing without RAG: {rag_error}")

            return {
                "success": True,
                "training_result": {"success": True, "data_processed": len(self.business_data)},
                "business_context": self._get_business_context(),
                "rag_indexing": indexing_result,
            }
        except Exception as e:
            logger.error(f"Error training business-specific AI: {str(e)}")
            return {"success": False, "error": f"Error training business-specific AI: {str(e)}"}

    def _get_business_context(self) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "business_id": self.business_id,
            "industry": self.industry,
            "data_available": list(self.business_data.keys()),
        }
        if "business_profile" in self.business_data:
            profile = self.business_data["business_profile"]
            context["business_name"] = profile.get("business_name", "Unknown")
            context["description"] = profile.get("description", "")
        return context

    def update_business_data(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update business data and retrain AI (deep merge preserves nested structures)."""
        try:
            normalized_new_data = self._normalize_business_data(new_data)

            if isinstance(self.business_data, dict) and isinstance(normalized_new_data, dict):
                self.business_data = self._deep_merge_dict(self.business_data, normalized_new_data)
            else:
                self.business_data = normalized_new_data

            training_result = self.train_with_business_data(self.business_data)
            return {
                "success": True,
                "training_result": training_result,
                "updated_fields": list(new_data.keys()),
            }
        except Exception as e:
            logger.error(f"Error updating business data: {str(e)}")
            return {"success": False, "error": f"Error updating business data: {str(e)}"}

    @staticmethod
    def _deep_merge_dict(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = BusinessSpecificAI._deep_merge_dict(result[key], value)
            else:
                result[key] = value
        return result

    # ── AI context generation (legacy; not used in onboarding or chat) ─

    def generate_ai_context_from_minimal_data(self) -> Dict[str, Any]:
        """Generate comprehensive business context from minimal data using AI.
        Legacy: no longer called during onboarding. Use only for standalone tools or debugging."""
        try:
            if not self.openai_api_key:
                return self._get_fallback_context()
            
            minimal_data = {
                "business_name": self._get_business_name(),
                "industry": self.industry,
                "description": self._get_business_description(),
                "products_services": self._get_products_services(),
                "contact_info": self._get_contact_info(),
            }

            context_prompt = f"""
Based on the minimal business information provided, generate comprehensive context
that would help an AI assistant understand and serve customers better:
            
            Business Information:
            {json.dumps(minimal_data, indent=2)}
            
            Generate the following context:
            1. Customer Personas (3-4 different types of customers)
            2. Business Positioning (how this business differentiates itself)
            3. Common Customer Concerns (what customers typically worry about)
            4. Conversation Strategies (how to approach different customer types)
            5. Value Propositions (key benefits and selling points)
            6. Industry Context (relevant industry knowledge and trends)
            
            Return as JSON with the following structure:
            {{
    "customer_personas": [{{"type": "string", "characteristics": "string", "needs": "string", "approach": "string"}}],
                "business_positioning": "string",
                "common_concerns": ["string"],
    "conversation_strategies": [{{"situation": "string", "approach": "string", "key_points": ["string"]}}],
                "value_propositions": ["string"],
    "industry_context": {{"trends": ["string"], "best_practices": ["string"], "common_challenges": ["string"]}}
            }}
            """
            client = self._get_openai_client()
            response = client.chat.completions.create(
                model=self.lightweight_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert business analyst and customer service strategist. "
                            "Generate comprehensive business context from minimal information "
                            "to help AI assistants serve customers better. Always respond with valid JSON."
                        ),
                    },
                    {"role": "user", "content": context_prompt},
                ],
                max_tokens=2000,
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            
            context_text = response.choices[0].message.content.strip()
            try:
                context = json.loads(context_text)
                return context if isinstance(context, dict) else self._get_fallback_context()
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI-generated context as JSON")
                return self._get_fallback_context()
            
        except Exception as e:
            logger.error(f"Error generating AI context: {str(e)}")
            return self._get_fallback_context()
    
    def _get_fallback_context(self) -> Dict[str, Any]:
        business_name = self._get_business_name()
        return {
            "customer_personas": [
                {
                    "type": "General Customer",
                    "characteristics": "Interested in the business services",
                    "needs": "Information and assistance",
                    "approach": "Be helpful and informative",
                }
            ],
            "business_positioning": f"{business_name} provides quality services in the {self.industry} industry",
            "common_concerns": [
                "Service quality and reliability",
                "Pricing transparency",
                "Response time and availability",
            ],
            "conversation_strategies": [
                {
                    "situation": "New customer inquiry",
                    "approach": "Be welcoming and informative",
                    "key_points": ["Introduce the business", "Ask about their needs", "Provide relevant information"],
                }
            ],
            "value_propositions": [
                "Quality service delivery",
                "Professional and responsive customer support",
            ],
            "industry_context": {
                "trends": ["Digital transformation", "Customer experience focus"],
                "best_practices": ["Quick response times", "Personalized service"],
                "common_challenges": ["Competition", "Customer retention"],
            },
        }

    # ── Standalone analysis (used only by /extract-intent and /analyze-sentiment APIs) ─
    
    def _analyze_sentiment(self, message: str) -> Dict[str, Any]:
        """Analyze customer sentiment. Used only by the /analyze-sentiment API endpoint."""
        try:
            if not self.openai_api_key:
                return {"sentiment": "neutral", "confidence": 0.5, "emotions": [], "urgency": "medium"}
            
            prompt = f"""
            Analyze the sentiment and emotions in this customer message: "{message}"
            
Return a JSON object with:
            - sentiment: positive, negative, or neutral
            - confidence: 0.0 to 1.0
            - emotions: list of detected emotions (e.g., frustrated, happy, confused)
            - urgency: high, medium, or low
            """
            client = self._get_openai_client()
            response = client.chat.completions.create(
                model=self.lightweight_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content.strip())
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {"sentiment": "neutral", "confidence": 0.5, "emotions": [], "urgency": "medium"}
    
    def _analyze_intent(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze customer intent. Used only by the /extract-intent API endpoint."""
        try:
            if not self.openai_api_key:
                return {"intent": "general_inquiry", "confidence": 0.5, "entities": {}, "metadata": {}}
            
            prompt = f"""
            Analyze the customer intent in this message: "{message}"
            
            For a {self.industry} business, classify the intent as one of:
            - product_inquiry: asking about products/services
            - pricing_inquiry: asking about prices/costs
            - appointment_booking: wanting to schedule/book something
            - payment_intent: wanting to make a payment, pay a bill, checkout, complete purchase
            - complaint: expressing dissatisfaction
            - compliment: expressing satisfaction
            - general_inquiry: general questions
            - support_request: needing help with existing service
            
Return a JSON object with: intent, confidence (0.0 to 1.0), entities (object), metadata (object)
            """
            client = self._get_openai_client()
            response = client.chat.completions.create(
                model=self.lightweight_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content.strip())
            result.setdefault("entities", {})
            result.setdefault("metadata", {})
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            return {"intent": "general_inquiry", "confidence": 0.5, "entities": {}, "metadata": {}}

    # ── Model status ───────────────────────────────────────────────────

    def _calculate_data_completeness(self) -> float:
        """Calculate data completeness percentage."""
        total_fields = 0
        filled_fields = 0

        for _category, data in self.business_data.items():
            if isinstance(data, dict):
                for _field, value in data.items():
                    total_fields += 1
                    if value and str(value).strip():
                        filled_fields += 1
            elif isinstance(data, list):
                total_fields += 1
                if data:
                    filled_fields += 1

        if total_fields == 0:
            return 0.0
        return (filled_fields / total_fields) * 100
