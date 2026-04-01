"""
Structured output models for the LangGraph customer agent.
The agent returns a CustomerResponse; the API serializes it directly.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class EscalationPayload(BaseModel):
    severity: str = Field(default="medium", description="critical, high, medium, low")
    context_summary: str = Field(default="", description="Summary of conversation context")
    suggested_action: str = Field(default="", description="Recommended next step")


class CustomerResponse(BaseModel):
    """Top-level response returned by the agent graph and sent to the API caller."""

    success: bool = True
    error: Optional[str] = Field(default=None, description="Error detail when success=False")
    response: str = Field(..., description="AI message text for the customer")
    intent: str = Field(default="general_inquiry")
    confidence: float = Field(default=0.8)
    sentiment: str = Field(default="neutral")
    escalation_required: bool = False
    escalation: Optional[EscalationPayload] = None
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    conversation_stage: str = Field(default="general_inquiry")
