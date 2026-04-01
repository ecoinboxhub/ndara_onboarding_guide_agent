"""
Business Owner AI - Minimal Inference API
Clean AI inference endpoints for business intelligence
"""

import logging
import os
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime

from ..core.business_intelligence import get_business_intelligence

logger = logging.getLogger(__name__)


# Pydantic models
class ChatRequest(BaseModel):
    query: str = Field(..., description="Business owner query")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class SalesAnalysisRequest(BaseModel):
    conversations: List[Dict[str, Any]] = Field(..., description="Conversation data")
    sales_data: Optional[List[Dict[str, Any]]] = Field(None, description="Sales transaction data")
    time_period: str = Field('last_30_days', description="Analysis period")


class SegmentCustomersRequest(BaseModel):
    customer_data: List[Dict[str, Any]] = Field(..., description="Customer profiles")
    method: str = Field('behavior', description="Segmentation method")


class BroadcastRequest(BaseModel):
    message_intent: str = Field(..., description="Message purpose")
    target_segment: str = Field(..., description="Target customer segment")
    business_data: Dict[str, Any] = Field(..., description="Business information")
    personalization_data: Optional[Dict[str, Any]] = None


class BusinessOwnerInferenceAPI:
    """Minimal inference API for Business Owner AI"""
    
    def __init__(self):
        self.app = FastAPI(
            title="ndara.ai Business Owner AI - Inference API",
            description="AI inference endpoints for business intelligence",
            version="1.0.0"
        )
        
        # Enable CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
        
        logger.info("Business Owner AI Inference API initialized")
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "ndara.ai Business Owner AI",
                "version": "1.0.0",
                "status": "operational",
                "docs": "/docs"
            }
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.post("/api/v1/chat")
        async def chat(business_id: str, industry: str, request: ChatRequest):
            """
            Process business owner query
            
            This is the main chat endpoint that handles all business intelligence queries including:
            - Sales analysis (e.g., "How are my sales performing?")
            - Customer segmentation (e.g., "Segment my customers")
            - Inventory retrieval/search (e.g., "Show me low stock items", "What products are out of stock?")
            - Invoice retrieval/search (e.g., "Show me unpaid invoices", "Find invoice INV-123")
            - Broadcast message preparation
            - General business intelligence queries
            
            
            Returns AI-generated business intelligence response with parsed query and guidance
            """
            try:
                bi = get_business_intelligence(business_id, industry)
                result = await bi.process_query(request.query, request.context or {})
                return result
            except Exception as e:
                logger.error(f"Error in chat: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/analyze-sales")
        async def analyze_sales(business_id: str, request: SalesAnalysisRequest):
            """
            Analyze sales performance
            
            Returns:
                - key_metrics: Sales KPIs
                - trends: Performance trends
                - insights: Actionable insights
                - recommendations: Strategic recommendations
            """
            try:
                from ..core.sales_analyzer import get_sales_analyzer
                analyzer = get_sales_analyzer(business_id)
                
                analysis = analyzer.analyze_sales_performance(
                    request.conversations,
                    request.sales_data,
                    request.time_period
                )
                
                return {
                    "success": True,
                    "analysis": analysis
                }
            except Exception as e:
                logger.error(f"Error analyzing sales: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/segment-customers")
        async def segment_customers(business_id: str, request: SegmentCustomersRequest):
            """
            Segment customers using ML
            
            Returns:
                - segments: Customer groups
                - segment_profiles: Characteristics of each segment
                - recommendations: Targeted strategies
            """
            try:
                from ..core.customer_segmentation import get_customer_segmentation
                segmenter = get_customer_segmentation(business_id)
                
                segmentation = segmenter.segment_customers(
                    request.customer_data,
                    request.method
                )
                
                return {
                    "success": True,
                    "segmentation": segmentation
                }
            except Exception as e:
                logger.error(f"Error segmenting customers: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/prepare-broadcast")
        async def prepare_broadcast(business_id: str, request: BroadcastRequest):
            """
            Prepare broadcast message
            
            Returns:
                - primary_message: Main message
                - variants: A/B test variants
                - call_to_action: Recommended CTA
                - recommended_send_time: Optimal timing
            """
            try:
                from ..core.broadcast_composer import get_broadcast_composer
                composer = get_broadcast_composer(business_id)
                
                broadcast = composer.compose_broadcast(
                    request.message_intent,
                    request.target_segment,
                    request.business_data,
                    request.personalization_data
                )
                
                return broadcast
            except Exception as e:
                logger.error(f"Error preparing broadcast: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/competitive-insights")
        async def competitive_insights(
            business_id: str,
            industry: str,
            business_data: Dict[str, Any],
            similar_businesses: Optional[List[Dict[str, Any]]] = None
        ):
            """
            Generate competitive intelligence
            
            Returns:
                - swot_analysis: Strengths, weaknesses, opportunities, threats
                - market_trends: Industry trends
                - competitive_advantages: Key differentiators
                - recommendations: Strategic recommendations
            """
            try:
                from ..core.competitive_intelligence import get_competitive_intelligence
                ci = get_competitive_intelligence(business_id, industry)
                
                analysis = ci.analyze_competitive_position(
                    business_data,
                    similar_businesses
                )
                
                return {
                    "success": True,
                    "analysis": analysis
                }
            except Exception as e:
                logger.error(f"Error generating competitive insights: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def run(self, host: str = '0.0.0.0', port: int = 8001):
        """Run the API server"""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port, log_level="info")
    
    def get_app(self):
        """Get FastAPI app instance"""
        return self.app


def create_app() -> FastAPI:
    """Create and return FastAPI app instance"""
    api = BusinessOwnerInferenceAPI()
    return api.get_app()


# For uvicorn
app = create_app()


if __name__ == "__main__":
    api = BusinessOwnerInferenceAPI()
    api.run(port=8001)
