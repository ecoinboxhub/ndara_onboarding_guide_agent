"""
Conversation Manager for Customer AI
Handles multi-turn conversation tracking, escalation detection, and analytics.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Single turn in a conversation"""
    role: str  # 'customer' or 'ai'
    message: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationManager:
    """
    Manages conversation flow, escalation detection, and analytics.
    """

    def __init__(self, business_id: str, max_history: int = 20, industry: str = "general"):
        self.business_id = business_id
        self.max_history = max_history
        self.industry = industry
        self.conversation_turns: List[ConversationTurn] = []
        self.customer_profile: Dict[str, Any] = {}

        # Conversation state
        self.current_stage = "greeting"
        self.conversation_start_time = datetime.now()
        self.last_activity = datetime.now()

        # Learning and optimisation
        self.conversation_insights: Dict[str, Any] = {}
        self.successful_patterns: List[Dict[str, Any]] = []
        self.optimization_suggestions: List[Dict[str, Any]] = []

    # ── Turn management ────────────────────────────────────────────────

    def add_turn(self, role: str, message: str, metadata: Dict[str, Any] = None) -> None:
        """Add a conversation turn."""
        turn = ConversationTurn(
            role=role,
            message=message,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        self.conversation_turns.append(turn)
        self.last_activity = datetime.now()

        if len(self.conversation_turns) > self.max_history:
            self.conversation_turns = self.conversation_turns[-self.max_history:]

        self._update_conversation_stage(role, message, metadata)

        if role == "customer":
            self._update_customer_profile(message, metadata)

    def _get_recent_turns(self, count: int) -> List[ConversationTurn]:
        return self.conversation_turns[-count:] if self.conversation_turns else []

    def _get_duration_text(self) -> str:
        duration = datetime.now() - self.conversation_start_time
        minutes = int(duration.total_seconds() / 60)
        if minutes < 1:
            return "Just started"
        elif minutes < 60:
            return f"{minutes} minutes"
        else:
            hours = minutes // 60
            remaining = minutes % 60
            return f"{hours}h {remaining}m"

    # ── Stage and profile tracking ─────────────────────────────────────

    def _update_conversation_stage(self, role: str, message: str, metadata: Optional[Dict[str, Any]]):
        if not metadata:
            return

        intent = metadata.get("intent", {})
        sentiment = metadata.get("sentiment", {})
        intent_type = intent.get("intent", "general_inquiry") if isinstance(intent, dict) else "general_inquiry"
        sentiment_type = sentiment.get("sentiment", "neutral") if isinstance(sentiment, dict) else "neutral"

        if intent_type == "complaint" and sentiment_type == "negative":
            self.current_stage = "complaint_resolution"
        elif intent_type == "appointment_booking":
            self.current_stage = "booking_assistance"
        elif intent_type == "pricing_inquiry":
            self.current_stage = "pricing_discussion"
        elif intent_type == "product_inquiry":
            self.current_stage = "product_exploration"
        elif sentiment_type == "positive":
            self.current_stage = "positive_engagement"
        elif len(self.conversation_turns) <= 2:
            self.current_stage = "greeting"
        else:
            self.current_stage = "general_inquiry"

    def _update_customer_profile(self, message: str, metadata: Optional[Dict[str, Any]]):
        if not metadata:
            return

        sentiment = metadata.get("sentiment", {})
        intent = metadata.get("intent", {})

        if isinstance(sentiment, dict):
            if sentiment.get("sentiment") == "negative":
                self.customer_profile["mood"] = "frustrated"
            elif sentiment.get("sentiment") == "positive":
                self.customer_profile["mood"] = "satisfied"
            if sentiment.get("urgency") == "high":
                self.customer_profile["urgency_level"] = "high"

        if isinstance(intent, dict):
            intent_type = intent.get("intent", "general_inquiry")
            if "interests" not in self.customer_profile:
                self.customer_profile["interests"] = []
            if intent_type not in self.customer_profile["interests"]:
                self.customer_profile["interests"].append(intent_type)

        message_lower = message.lower()
        if any(w in message_lower for w in ["morning", "afternoon", "evening"]):
            self.customer_profile["time_preference"] = "specified"
        if len(message) > 100:
            self.customer_profile["communication_style"] = "detailed"
        elif len(message) < 20:
            self.customer_profile["communication_style"] = "brief"

    # ── Escalation ─────────────────────────────────────────────────────

    def classify_complaint_severity(self, message: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classify complaint severity with industry-specific triggers.
        Returns severity, escalate_immediately, reason, context_summary, suggested_action.
        """
        try:
            message_lower = message.lower()

            try:
                from ..domain.industries.config import get_escalation_triggers, get_escalation_recommendation
                triggers = get_escalation_triggers(self.industry)
                critical_indicators = triggers.get("critical", [
                    "lawsuit", "legal action", "lawyer", "police", "fraud", "scam",
                    "stolen", "threat", "danger", "urgent", "emergency",
                ])
                high_severity_indicators = triggers.get("high", [
                    "worst", "terrible", "refund", "money back", "cancel",
                    "never again", "report", "complaint",
                ])
                medium_severity_indicators = triggers.get("medium", [
                    "disappointed", "unhappy", "frustrated", "problem", "issue",
                    "wrong", "mistake", "not working", "broken",
                ])
            except ImportError:
                critical_indicators = [
                    "lawsuit", "legal action", "lawyer", "sue", "police",
                    "fraud", "scam", "stolen", "threat", "danger",
                    "immediately", "right now", "asap", "urgent", "emergency",
                ]
                high_severity_indicators = [
                    "worst", "terrible", "horrible", "disgusting", "outraged",
                    "furious", "angry", "unacceptable", "ridiculous", "pathetic",
                    "refund", "money back", "cancel", "never again", "report",
                ]
                medium_severity_indicators = [
                    "disappointed", "unhappy", "frustrated", "concerned", "worried",
                    "problem", "issue", "wrong", "mistake", "error",
                    "not working", "broken", "doesn't work", "poor quality",
                ]

            critical_count = sum(1 for ind in critical_indicators if ind in message_lower)
            high_count = sum(1 for ind in high_severity_indicators if ind in message_lower)
            medium_count = sum(1 for ind in medium_severity_indicators if ind in message_lower)

            sentiment_score = 0.0
            if metadata and "sentiment" in metadata:
                sentiment_data = metadata.get("sentiment", {})
                if isinstance(sentiment_data, dict):
                    sentiment_score = sentiment_data.get("score", 0.0)

            repeated_complaints = False
            if len(self.conversation_turns) >= 4:
                recent_customer_messages = [
                    turn.message.lower() for turn in self.conversation_turns[-6:] if turn.role == "customer"
                ]
                complaint_words = ["problem", "issue", "wrong", "not working", "disappointed"]
                complaint_count = sum(
                    1 for msg in recent_customer_messages if any(w in msg for w in complaint_words)
                )
                repeated_complaints = complaint_count >= 2

            severity = "low"
            escalate_immediately = False
            reason = ""

            if critical_count > 0:
                severity = "critical"
                escalate_immediately = True
                reason = f"Critical keywords detected: {critical_count} instances"
            elif high_count >= 2 or (high_count >= 1 and sentiment_score < -0.6):
                severity = "high"
                escalate_immediately = True
                reason = f"High severity indicators: {high_count} instances, sentiment: {sentiment_score}"
            elif (high_count >= 1 or medium_count >= 2) and repeated_complaints:
                severity = "high"
                escalate_immediately = True
                reason = "Repeated complaints detected with negative sentiment"
            elif medium_count >= 2 or (medium_count >= 1 and sentiment_score < -0.4):
                severity = "medium"
                escalate_immediately = False
                reason = f"Medium severity indicators: {medium_count} instances"
            else:
                severity = "low"
                escalate_immediately = False
                reason = "Minor concern or inquiry"

            try:
                from ..domain.industries.config import get_escalation_recommendation
                suggested_action = get_escalation_recommendation(self.industry, severity)
            except ImportError:
                suggested_action = (
                    "Escalate to business owner immediately. Legal/safety implications."
                    if severity == "critical"
                    else "Escalate to business owner. Customer is very upset and may churn."
                    if severity == "high"
                    else "Attempt resolution. Escalate if customer remains unsatisfied."
                    if severity == "medium"
                    else "Address concern professionally. Monitor for escalation."
                )

            context_summary = self._generate_complaint_context_summary(severity)

            return {
                "severity": severity,
                "escalate_immediately": escalate_immediately,
                "reason": reason,
                "context_summary": context_summary,
                "suggested_action": suggested_action,
                "indicators": {"critical": critical_count, "high": high_count, "medium": medium_count},
                "sentiment_score": sentiment_score,
                "repeated_complaints": repeated_complaints,
            }

        except Exception as e:
            logger.error(f"Error classifying complaint severity: {str(e)}")
            return {"severity": "medium", "escalate_immediately": False, "reason": "Error in classification", "error": str(e)}

    def _generate_complaint_context_summary(self, severity: str) -> str:
        try:
            parts = [
                f"Complaint Severity: {severity.upper()}",
                f"Conversation Duration: {self._get_duration_text()}",
                f"Total Exchanges: {len(self.conversation_turns) // 2}",
            ]
            recent_turns = self._get_recent_turns(4)
            if recent_turns:
                parts.append("\nRecent Conversation:")
                for turn in recent_turns:
                    role = "Customer" if turn.role == "customer" else "AI"
                    parts.append(f"{role}: {turn.message[:100]}...")
            if self.customer_profile:
                parts.append("\nCustomer Profile:")
                parts.append(f"- Mood: {self.customer_profile.get('mood', 'unknown')}")
                parts.append(f"- Urgency: {self.customer_profile.get('urgency_level', 'normal')}")
            return "\n".join(parts)
        except Exception as e:
            logger.error(f"Error generating context summary: {str(e)}")
            return "Unable to generate context summary"

    def should_escalate_to_human(self) -> bool:
        """Determine if conversation should be escalated to a human.
        
        Result is cached per turn count so repeat calls within the same
        request don't re-evaluate the full logic.
        """
        current_count = len(self.conversation_turns)
        if hasattr(self, "_escalation_cache") and self._escalation_cache[0] == current_count:
            return self._escalation_cache[1]

        result = self._evaluate_escalation()
        self._escalation_cache = (current_count, result)
        return result

    def _evaluate_escalation(self) -> bool:
        """Core escalation evaluation logic (uncached)."""
        if self.customer_profile.get("mood") == "frustrated" and len(self.conversation_turns) > 6:
            return True
        if self.customer_profile.get("urgency_level") == "high":
            return True

        recent_ai_turns = [t for t in self.conversation_turns[-6:] if t.role == "ai"]
        if len(recent_ai_turns) >= 3:
            customer_msgs = [t.message.lower() for t in self.conversation_turns[-6:] if t.role == "customer"]
            if len(set(customer_msgs)) <= 2:
                return True

        if self.conversation_turns:
            latest_customer_turn = next(
                (t for t in reversed(self.conversation_turns) if t.role == "customer"), None
            )
            if latest_customer_turn:
                severity_result = self.classify_complaint_severity(
                    latest_customer_turn.message, latest_customer_turn.metadata
                )
                if severity_result.get("escalate_immediately"):
                    return True

        return False

    def get_escalation_payload(self) -> Dict[str, Any]:
        """
        Get top-level escalation fields for chat response.
        Returns escalation_required and full escalation object for backend.
        """
        escalation_required = self.should_escalate_to_human()
        escalation = None
        if escalation_required:
            latest_customer_turn = None
            if self.conversation_turns:
                latest_customer_turn = next(
                    (t for t in reversed(self.conversation_turns) if t.role == "customer"), None
                )
            if latest_customer_turn:
                sr = self.classify_complaint_severity(latest_customer_turn.message, latest_customer_turn.metadata)
                escalation = {
                    "severity": sr.get("severity", "medium"),
                    "context_summary": sr.get("context_summary", ""),
                    "suggested_action": sr.get("suggested_action", ""),
                    "reason": sr.get("reason", ""),
                }
            else:
                sev = "high" if self.customer_profile.get("urgency_level") == "high" else "medium"
                escalation = {
                    "severity": sev,
                    "context_summary": self._generate_complaint_context_summary(sev),
                    "suggested_action": "Connect with customer relations manager",
                    "reason": "Escalation triggered by conversation pattern or customer profile",
                }
        return {"escalation_required": escalation_required, "escalation": escalation}

    # ── Analytics ──────────────────────────────────────────────────────

    def get_conversation_analytics(self) -> Dict[str, Any]:
        if not self.conversation_turns:
            return {}

        customer_turns = [t for t in self.conversation_turns if t.role == "customer"]
        ai_turns = [t for t in self.conversation_turns if t.role == "ai"]

        total_duration = (datetime.now() - self.conversation_start_time).total_seconds()
        avg_response_time = total_duration / len(ai_turns) if ai_turns else 0
        customer_lengths = [len(t.message) for t in customer_turns]
        avg_customer_msg_len = sum(customer_lengths) / len(customer_lengths) if customer_lengths else 0

        return {
            "conversation_metrics": {
                "total_turns": len(self.conversation_turns),
                "customer_turns": len(customer_turns),
                "ai_turns": len(ai_turns),
                "duration_seconds": total_duration,
                "avg_response_time_seconds": avg_response_time,
                "avg_customer_message_length": avg_customer_msg_len,
            },
            "conversation_quality": {
                "stage": self.current_stage,
                "customer_mood": self.customer_profile.get("mood", "neutral"),
                "escalation_needed": self.should_escalate_to_human(),
                "engagement_level": self._calculate_engagement_level(),
            },
            "customer_insights": self.customer_profile,
        }

    def _calculate_engagement_level(self) -> str:
        if not self.conversation_turns:
            return "none"
        customer_turns = [t for t in self.conversation_turns if t.role == "customer"]
        if len(customer_turns) <= 2:
            return "low"
        elif len(customer_turns) <= 5:
            return "medium"
        return "high"

    # ── Feedback / learning ────────────────────────────────────────────

    def learn_from_conversation(self, conversation_outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Learn from conversation outcomes and optimise future interactions."""
        try:
            insights = self._extract_conversation_insights(conversation_outcome)

            if conversation_outcome.get("success", False):
                self._update_successful_patterns(insights)

            suggestions = self._generate_optimization_suggestions(insights)
            self.conversation_insights.update(insights)
            self.optimization_suggestions.extend(suggestions)

            return {
                "success": True,
                "insights": insights,
                "suggestions": suggestions,
                "updated_patterns": len(self.successful_patterns),
            }
        except Exception as e:
            logger.error(f"Error learning from conversation: {str(e)}")
            return {"success": False, "error": str(e)}

    def _extract_conversation_insights(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "conversation_length": len(self.conversation_turns),
            "duration_minutes": (datetime.now() - self.conversation_start_time).total_seconds() / 60,
            "final_stage": self.current_stage,
            "customer_satisfaction": outcome.get("satisfaction_score", 0),
            "goal_achieved": outcome.get("goal_achieved", False),
            "escalation_needed": outcome.get("escalation_needed", False),
            "common_topics": self._identify_common_topics(),
            "response_patterns": self._analyze_response_patterns(),
            "customer_behavior": self._analyze_customer_behavior(),
        }

    def _update_successful_patterns(self, insights: Dict[str, Any]) -> None:
        if insights.get("goal_achieved", False) and insights.get("customer_satisfaction", 0) > 0.7:
            pattern = {
                "timestamp": datetime.now().isoformat(),
                "conversation_stage": insights.get("final_stage"),
                "duration_minutes": insights.get("duration_minutes"),
                "turn_count": insights.get("conversation_length"),
                "topics": insights.get("common_topics", []),
                "response_style": insights.get("response_patterns", {}),
                "customer_type": insights.get("customer_behavior", {}).get("type", "unknown"),
            }
            self.successful_patterns.append(pattern)
            if len(self.successful_patterns) > 50:
                self.successful_patterns = self.successful_patterns[-50:]

    def _generate_optimization_suggestions(self, insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        if insights.get("duration_minutes", 0) > 10:
            suggestions.append({"type": "efficiency", "suggestion": "Consider more direct responses for common questions", "priority": "medium"})
        if insights.get("escalation_needed", False):
            suggestions.append({"type": "escalation", "suggestion": "Improve FAQ coverage for frequently escalated topics", "priority": "high"})
        if insights.get("customer_satisfaction", 0) < 0.6:
            suggestions.append({"type": "satisfaction", "suggestion": "Review response tone and helpfulness", "priority": "high"})
        if insights.get("conversation_length", 0) > 15:
            suggestions.append({"type": "flow", "suggestion": "Consider proactive suggestions to move conversation forward", "priority": "medium"})
        return suggestions

    def _identify_common_topics(self) -> List[str]:
        topics = []
        for turn in self.conversation_turns:
            if turn.role == "customer":
                msg = turn.message.lower()
                if any(w in msg for w in ["price", "cost", "expensive"]):
                    topics.append("pricing")
                elif any(w in msg for w in ["schedule", "appointment", "time"]):
                    topics.append("scheduling")
                elif any(w in msg for w in ["service", "help", "support"]):
                    topics.append("service")
                elif any(w in msg for w in ["location", "address", "where"]):
                    topics.append("location")
                elif any(w in msg for w in ["hours", "open", "close"]):
                    topics.append("hours")
        return list(set(topics))

    def _analyze_response_patterns(self) -> Dict[str, Any]:
        patterns: Dict[str, Any] = {
            "avg_response_length": 0,
            "question_ratio": 0,
            "suggestion_ratio": 0,
            "information_ratio": 0,
        }
        ai_turns = [t for t in self.conversation_turns if t.role == "ai"]
        if ai_turns:
            total_length = sum(len(t.message) for t in ai_turns)
            patterns["avg_response_length"] = total_length / len(ai_turns)
            patterns["question_ratio"] = sum(1 for t in ai_turns if "?" in t.message) / len(ai_turns)
            patterns["suggestion_ratio"] = sum(
                1 for t in ai_turns if any(w in t.message.lower() for w in ["suggest", "recommend", "consider"])
            ) / len(ai_turns)
            patterns["information_ratio"] = sum(
                1 for t in ai_turns if any(w in t.message.lower() for w in ["is", "are", "have", "can"])
            ) / len(ai_turns)
        return patterns

    def _analyze_customer_behavior(self) -> Dict[str, Any]:
        behavior: Dict[str, Any] = {
            "type": "unknown",
            "communication_style": "unknown",
            "urgency_level": "normal",
            "information_seeking": False,
        }
        customer_turns = [t for t in self.conversation_turns if t.role == "customer"]
        if customer_turns:
            avg_length = sum(len(t.message) for t in customer_turns) / len(customer_turns)
            if avg_length > 100:
                behavior["communication_style"] = "detailed"
            elif avg_length < 30:
                behavior["communication_style"] = "brief"
            else:
                behavior["communication_style"] = "moderate"

            urgent_words = ["urgent", "asap", "immediately", "quickly", "fast"]
            if any(any(w in t.message.lower() for w in urgent_words) for t in customer_turns):
                behavior["urgency_level"] = "high"

            question_count = sum(1 for t in customer_turns if "?" in t.message)
            if question_count > len(customer_turns) * 0.5:
                behavior["information_seeking"] = True

            if behavior["information_seeking"] and behavior["communication_style"] == "detailed":
                behavior["type"] = "researcher"
            elif behavior["urgency_level"] == "high":
                behavior["type"] = "urgent"
            elif behavior["communication_style"] == "brief":
                behavior["type"] = "efficient"
            else:
                behavior["type"] = "standard"
        return behavior
