"""
Inference API for Customer AI (LangGraph agent backend).
AI inference endpoints only — no business logic.
"""

import logging
import os
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
import json
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from ..core.customer_ai_orchestrator import get_orchestrator

logger = logging.getLogger(__name__)


# Pydantic request/response models
class BusinessInfo(BaseModel):
    """Business information structure"""
    name: str = Field(..., description="Business name")
    description: Optional[str] = Field("", description="Business description")
    phone: Optional[str] = Field("", description="Business phone number")
    email: Optional[str] = Field(None, description="Business email")
    address: Optional[str] = Field("", description="Business address")
    timezone: str = Field("Africa/Lagos", description="Business timezone")
    whatsapp_number: Optional[str] = Field(None, description="WhatsApp display phone number")


class FAQ(BaseModel):
    """FAQ structure"""
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None


class Policies(BaseModel):
    """Business policies"""
    return_policy: Optional[str] = Field("", description="Return/refund policy")
    shipping_policy: Optional[str] = Field("", description="Shipping policy")
    payment_methods: Optional[str] = Field("", description="Accepted payment methods")


class ShippingInfo(BaseModel):
    """Shipping information (ecommerce-focused)."""
    methods: List[str] = Field(default_factory=list, description="Shipping methods supported")
    regions: List[str] = Field(default_factory=list, description="Regions covered for shipping")
    estimated_delivery: Optional[str] = Field(None, description="Estimated delivery window")
    shipping_fee: Optional[float] = Field(None, description="Default shipping fee")
    free_shipping_threshold: Optional[float] = Field(None, description="Threshold for free shipping, if any")


class BankDetails(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None


class PaymentDetails(BaseModel):
    """Payment details shown to customers (does not create payment links)."""
    accepted_methods: List[str] = Field(default_factory=list, description="Accepted payment methods")
    currency: str = Field("NGN", description="Currency code")
    bank_details: Optional[BankDetails] = None
    payment_instructions: Optional[str] = None


class BusinessHoursDay(BaseModel):
    open: Optional[str] = None
    close: Optional[str] = None
    is_closed: bool = False


class AISettings(BaseModel):
    """AI configuration settings"""
    personality: str = Field("professional", description="AI personality type")
    language: str = Field("en", description="Response language")
    response_style: str = Field("professional_friendly", description="Response style")
    enable_tools: List[str] = Field(
        default_factory=lambda: [
            "product_search",
            "get_product_by_id",
            "check_availability",
            "book_appointment",
            "get_business_hours",
        ],
        description="List of enabled tools",
    )


class KnowledgeData(BaseModel):
    """Complete business knowledge data structure matching backend payload.
    Product/service catalog is provided via backend AI Tools (product_search, get_product_by_id), not in onboarding."""
    collection_name: Optional[str] = Field(None, description="Business collection name / slug (stable identifier)")
    business_info: BusinessInfo
    faqs: List[FAQ] = Field(default_factory=list, description="Frequently asked questions")
    policies: Optional[Policies] = Field(default_factory=lambda: Policies(return_policy="", shipping_policy="", payment_methods=""), description="Business policies")
    shipping_info: Optional[ShippingInfo] = Field(default=None, description="Shipping info (optional)")
    payment_details: Optional[PaymentDetails] = Field(default=None, description="Payment details (optional)")
    business_hours: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Business operating hours (day-based structure with open/close/is_closed)")
    ai_enabled: Optional[bool] = Field(default=True, description="Whether AI is enabled for this business")
    ai_settings: Optional[AISettings] = Field(default=None, description="AI configuration settings")
    
    class Config:
        """Pydantic config"""
        extra = "allow"
        json_schema_extra = {
            "example": {
                "collection_name": "business_slug_123",
                "business_info": {
                    "name": "Example Business",
                    "description": "A great business",
                    "phone": "+1234567890",
                    "email": "contact@example.com",
                    "address": "123 Main St",
                    "timezone": "Africa/Lagos",
                    "whatsapp_number": "+1234567890"
                },
                "faqs": [],
                "policies": {
                    "return_policy": "",
                    "shipping_policy": "",
                    "payment_methods": ""
                },
                "shipping_info": {
                    "methods": ["Standard Shipping"],
                    "regions": ["Nationwide"],
                    "estimated_delivery": "3-5 business days",
                    "shipping_fee": 0.0,
                    "free_shipping_threshold": None
                },
                "payment_details": {
                    "accepted_methods": ["Cash", "Bank Transfer", "Card"],
                    "currency": "NGN",
                    "bank_details": {
                        "bank_name": "",
                        "account_number": "",
                        "account_name": ""
                    },
                    "payment_instructions": ""
                },
                "business_hours": {
                    "monday": {"open": "09:00", "close": "17:00", "is_closed": False}
                },
                "ai_enabled": True,
                "ai_settings": {
                    "personality": "professional",
                    "language": "en",
                    "response_style": "professional_friendly",
                    "enable_tools": ["product_search", "check_availability", "book_appointment"]
                }
            }
        }


class ChatRequest(BaseModel):
    message: str = Field(..., description="Customer message")
    customer_id: Optional[str] = Field(None, description="Customer identifier")
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context. Keys: conversation_id (stable per chat), channel (e.g. 'whatsapp', 'voice'), "
        "is_first_interaction (bool) = first time ever → AI gives introduction, "
        "is_new_day (bool) = first message today / after 24h → AI gives time-of-day greeting, "
        "conversation_history (list of {role: 'customer'|'ai', message: '...'}) = prior turns for follow-up and memory. "
        "Send conversation_history on every request so the AI can answer follow-ups (e.g. 'Yes', 'Yes pls')."
    )


class IntentRequest(BaseModel):
    message: str = Field(..., description="Message to analyze")


class SentimentRequest(BaseModel):
    message: str = Field(..., description="Message to analyze")


class FeedbackRequest(BaseModel):
    customer_id: Optional[str] = Field(None, description="Customer identifier")
    conversation_id: Optional[str] = Field(None, description="Conversation identifier (use when conversation was scoped by conversation_id)")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context with customer_id/conversation_id (matches process_customer_message scoping)")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_text: Optional[str] = Field(None, description="Optional feedback text")


class EscalationRequest(BaseModel):
    """Escalation registration - called by backend when escalation_required in chat response"""
    conversation_id: str = Field(..., description="Conversation identifier")
    customer_id: str = Field(..., description="Customer identifier")
    reason: str = Field(..., description="Escalation reason (e.g., complaint_severity_high)")
    severity: str = Field(..., description="Severity level: critical, high, medium, low")
    context_summary: str = Field(..., description="Summary of conversation context")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Recent conversation turns")
    customer_message: Optional[str] = Field(None, description="Last customer message")
    ai_response: Optional[str] = Field(None, description="Last AI response")


class InferenceAPI:
    """
    Minimal inference API for Customer AI system
    Focus: AI inference endpoints only
    """
    
    def __init__(self):
        self.app = FastAPI(
            title="ndara.ai Customer AI - Inference API",
            description="AI inference endpoints powered by LangGraph agent",
            version="3.0.0"
        )

        # Rate limiting — configurable via env; defaults: chat 60/min, onboard 10/min
        self._limiter = Limiter(key_func=get_remote_address)
        self.app.state.limiter = self._limiter
        self.app.add_exception_handler(
            RateLimitExceeded,
            lambda req, exc: JSONResponse(
                status_code=429,
                content={"success": False, "error": "Too many requests. Please slow down."},
            ),
        )
        self.app.add_middleware(SlowAPIMiddleware)

        # Enable CORS
        # Get CORS origins from environment (default to "*" for development)
        cors_origins = os.getenv('CORS_ORIGINS', '*')
        if cors_origins == '*':
            # Development mode - allow all origins
            # Note: Cannot use credentials with wildcard origins (CORS spec)
            allow_origins = ["*"]
            allow_credentials = False
        else:
            # Production mode - specific origins (comma-separated)
            # Can use credentials with specific origins
            allow_origins = [origin.strip() for origin in cors_origins.split(',')]
            allow_credentials = True
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Get orchestrator
        self.orchestrator = get_orchestrator()
        
        # Setup routes
        self._setup_routes()
        
        logger.info("Inference API initialized")
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        def root():
            """Root endpoint"""
            return {
                "service": "ndara.ai Customer AI",
                "version": "3.0.0",
                "framework": "LangGraph",
                "status": "operational",
                "docs": "/docs",
                "health": "/health"
            }

        @self.app.get("/health")
        def health_check():
            """Health check endpoint — checks real dependency connectivity."""
            checks: Dict[str, Any] = {}

            # 1. OpenAI API key present (not a live call — too slow for health check)
            checks["openai_key_set"] = bool(os.getenv("OPENAI_API_KEY"))

            # 2. Backend AI Tools URL reachable
            tools_url = (os.getenv("AI_TOOLS_URL") or "").strip()
            if tools_url:
                try:
                    import httpx
                    r = httpx.get(tools_url.rstrip("/").rsplit("/", 1)[0] + "/", timeout=3.0)
                    checks["backend_tools"] = r.status_code < 500
                except Exception:
                    checks["backend_tools"] = False
            else:
                checks["backend_tools"] = False

            # 3. Vector store connectivity
            try:
                storage_mode = os.getenv("VECTOR_STORAGE_MODE", "pgvector")
                if storage_mode == "local":
                    checks["vector_store"] = True  # ChromaDB is in-process
                else:
                    # pgvector — quick TCP connect to Postgres
                    import socket
                    host = os.getenv("POSTGRES_HOST", "localhost")
                    port = int(os.getenv("POSTGRES_PORT", "5432"))
                    s = socket.create_connection((host, port), timeout=2)
                    s.close()
                    checks["vector_store"] = True
            except Exception:
                checks["vector_store"] = False

            # 4. Orchestrator internal status
            status = self.orchestrator.get_system_status()
            checks["orchestrator"] = status.get("success", False)

            overall = "healthy" if all(checks.values()) else "degraded"
            return {
                "status": overall,
                "timestamp": datetime.now().isoformat(),
                "checks": checks,
                "details": status,
            }

        _onboard_limit = os.getenv("RATE_LIMIT_ONBOARD", "10/minute")
        _chat_limit = os.getenv("RATE_LIMIT_CHAT", "60/minute")

        @self.app.post("/api/v1/onboard")
        @self._limiter.limit(_onboard_limit)
        def onboard_business(
            request: Request,
            business_id: Optional[str] = None,
            body: Dict[str, Any] = Body(...)
        ):
            """
            Onboard a new business and train AI
            
            Supports two formats for backward compatibility:
            1. New format: business_id as query parameter, KnowledgeData in body
               POST /api/v1/onboard?business_id=1
               Body: { "business_info": {...}, "products": [...], ... }
            
            2. Legacy format: business_id in request body (wrapped)
               POST /api/v1/onboard
               Body: { "business_id": "1", "business_data": {...} }
            
            Args:
                business_id: Business identifier (query parameter, optional for legacy support)
                body: Request body - either KnowledgeData directly or legacy format with business_id and business_data
            
            Returns:
                - success: bool
                - business_id: str
                - industry: str
                - confidence: float
                - model_info: dict
            """
            try:
                # Determine business_id and knowledge_data based on format
                if business_id is None:
                    # Legacy format: business_id in body; new format may send collection_name instead
                    business_id = body.get('business_id') or body.get('collection_name')
                    if not business_id:
                        raise HTTPException(
                            status_code=400,
                            detail="business_id is required (either as query parameter, or in request body as business_id/collection_name)"
                        )
                    # Extract business_data from legacy format
                    business_data_dict = body.get('business_data', body)
                else:
                    # New format: business_id from query parameter
                    # Body should be KnowledgeData structure
                    business_data_dict = body
                
                # Validate knowledge_data structure
                try:
                    # Try to parse as KnowledgeData to validate structure
                    knowledge_data = KnowledgeData(**business_data_dict)
                    # Convert Pydantic model to dict for orchestrator
                    business_data_dict = knowledge_data.model_dump()
                    
                    # Provide defaults for missing optional fields
                    if business_data_dict.get('ai_settings') is None:
                        business_data_dict['ai_settings'] = {
                            'personality': 'professional',
                            'language': 'en',
                            'response_style': 'professional_friendly',
                            'enable_tools': [
                                'product_search',
                                'get_product_by_id',
                                'check_availability',
                                'book_appointment',
                                'get_business_hours',
                            ]
                        }
                    if not business_data_dict.get('business_hours'):
                        business_data_dict['business_hours'] = {}
                    if not business_data_dict.get('policies'):
                        business_data_dict['policies'] = {
                            'return_policy': '',
                            'shipping_policy': '',
                            'payment_methods': ''
                        }
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid knowledge_data structure: {str(e)}"
                    )
                
                result = self.orchestrator.onboard_business(
                    business_id,
                    business_data_dict
                )
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error onboarding business: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal error during onboarding. Check server logs.")
        
        @self.app.post("/api/v1/chat")
        @self._limiter.limit(_chat_limit)
        def chat(request: Request, business_id: str, body: ChatRequest):
            """
            Process customer message and generate AI response
            
            Args:
                business_id: Business identifier (query param)
                request: Chat request with message, customer_id, context
            
            Returns:
                - success: bool
                - response: str (AI generated response)
                - intent: str
                - sentiment: str
                - confidence: float
                - escalation_required: bool
                - structured_data: dict (e.g., appointment details, product info)
            """
            try:
                # Ensure business_id is a string for consistency
                business_id = str(business_id)
                
                # Log for debugging — do NOT log message content (may contain PII)
                logger.info(f"Processing chat for business_id: {business_id}")
                
                result = self.orchestrator.process_customer_message(
                    business_id=business_id,
                    customer_message=body.message,
                    customer_id=body.customer_id,
                    context=body.context
                )
                
                if not result['success']:
                    error_detail = result.get('error', 'Unknown error')
                    logger.error(f"Chat failed for business_id {business_id}: {error_detail}")
                    raise HTTPException(status_code=400, detail=error_detail)
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error processing chat: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal error processing message. Please try again.")
        
        @self.app.post("/api/v1/extract-intent")
        def extract_intent(business_id: str, request: IntentRequest):
            """
            Extract intent from customer message
            
            Returns:
                - success: bool
                - intent: str (e.g., 'book_appointment', 'product_inquiry', 'complaint')
                - confidence: float
                - entities: dict (extracted entities like dates, products, locations)
                - metadata: dict
            """
            try:
                result = self.orchestrator.extract_intent(business_id, request.message)
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error extracting intent: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal error extracting intent.")
        
        @self.app.post("/api/v1/analyze-sentiment")
        def analyze_sentiment(business_id: str, request: SentimentRequest):
            """
            Analyze sentiment of customer message
            
            Returns:
                - success: bool
                - sentiment: str ('positive', 'negative', 'neutral')
                - score: float (-1.0 to 1.0)
                - confidence: float
            """
            try:
                result = self.orchestrator.analyze_sentiment(business_id, request.message)
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error analyzing sentiment: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal error analyzing sentiment.")
        
        @self.app.post("/api/v1/feedback")
        def process_feedback(business_id: str, request: FeedbackRequest):
            """
            Process customer feedback for AI learning
            
            Args:
                business_id: Business identifier
                request: Feedback with rating and optional text
            
            Returns:
                - success: bool
                - learning_result: dict
                - message: str
            """
            try:
                # Pass None (not "") when customer_id absent so orchestrator scoping treats it as unset
                customer_id_val = request.customer_id if request.customer_id else None
                result = self.orchestrator.process_feedback(
                    business_id=business_id,
                    customer_id=customer_id_val,
                    rating=request.rating,
                    feedback_text=request.feedback_text,
                    conversation_id=request.conversation_id,
                    context=request.context
                )
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error processing feedback: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal error processing feedback.")
        
        @self.app.post("/api/v1/escalate")
        def register_escalation(business_id: str, request: EscalationRequest):
            """
            Register an escalation to human/business owner.
            Backend calls this after detecting escalation_required in chat response.
            Returns escalation_id, recommended_action, and context_for_agent.
            """
            try:
                result = self.orchestrator.register_escalation(
                    business_id=str(business_id),
                    conversation_id=request.conversation_id,
                    customer_id=request.customer_id,
                    reason=request.reason,
                    severity=request.severity,
                    context_summary=request.context_summary,
                    conversation_history=request.conversation_history,
                    customer_message=request.customer_message,
                    ai_response=request.ai_response,
                )
                if not result.get("success"):
                    raise HTTPException(status_code=400, detail=result.get("error"))
                return result
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error registering escalation: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal error registering escalation.")

        @self.app.get("/api/v1/model-status")
        def get_model_status(business_id: str):
            """
            Get AI model status for a business
            
            Returns:
                - success: bool
                - business_id: str
                - industry: str
                - model_type: str ('base_model', 'industry_model', 'business_model')
                - model_id: str
                - data_completeness: float
                - last_updated: str (ISO format)
            """
            try:
                result = self.orchestrator.get_model_status(business_id)
                
                if not result['success']:
                    raise HTTPException(status_code=404, detail=result.get('error'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting model status: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal error getting model status.")
    
    def run(self, host: str = '0.0.0.0', port: int = 8000):
        """Run the API server"""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port, log_level="info")
    
    def get_app(self):
        """Get FastAPI app instance"""
        return self.app


def create_app() -> FastAPI:
    """Create and return FastAPI app instance"""
    api = InferenceAPI()
    return api.get_app()

