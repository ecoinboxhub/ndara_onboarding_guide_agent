"""
Prompt Processor
Applies call-specific prompt rules: Nigerian English tone, smart brevity,
verification/clarification, and progressive disclosure before sending to TTS.
Optimized for real-time voice: natural boundaries, 3-5 sentences for complex topics.
"""

import re
from typing import Dict, Any, List


class PromptProcessor:
    """Apply prompt catalog rules to AI responses before TTS"""

    # ~2.5 words/sec natural speech; 5 sec default = ~12-15 words/sentence * 4-5 sentences
    WORDS_PER_SECOND = 2.5
    MAX_SENTENCES_SIMPLE = 3
    MAX_SENTENCES_COMPLEX = 5

    def __init__(self, turn_budget_seconds: float = 5.0):
        self.turn_budget_seconds = turn_budget_seconds

    def process_response(self, context: Dict[str, Any], response_text: str) -> str:
        """
        Transform response to match call style: short, Nigerian English tone, micro‑confirmations.
        Uses smart brevity: 3-5 sentences for complex topics, natural boundaries (no mid-thought cuts).
        """
        text = response_text.strip()
        if not text:
            return "Alright. Could you say that again, please?"

        # Convert bullets/lists to spoken prose (Customer AI may still send markdown occasionally)
        text = self._bullet_to_prose(text)

        # Smart brevity: allow 3-5 sentences based on complexity, stop at natural boundaries
        sentences = self._split_sentences(text)
        max_sentences = (
            self.MAX_SENTENCES_COMPLEX
            if self._is_complex_topic(text, sentences)
            else self.MAX_SENTENCES_SIMPLE
        )
        added_confirmation = False
        if len(sentences) > max_sentences:
            sentences = sentences[:max_sentences]
            trimmed = " ".join(sentences).strip()
            if not trimmed.endswith((".", "!", "?")):
                trimmed += "."
            # When both critical details and trimmed: use one combined phrase to avoid back-to-back questions
            if self._contains_critical_detail(trimmed):
                text = f"{trimmed} Is that correct, or would you like me to go into more detail?"
                added_confirmation = True
            else:
                text = f"{trimmed} Would you like me to go into more detail?"
        else:
            text = " ".join(sentences)

        # Nigerian English tone tweaks (light touch, avoid overdoing)
        text = self._apply_nigerian_tone(text)

        # Ensure micro‑confirmation when giving details (time, money, location)
        if self._contains_critical_detail(text) and not added_confirmation:
            text = f"{text} Is that correct?"

        # Add human-like conversation patterns
        text = self._add_human_patterns(text, context)

        return text

    def _bullet_to_prose(self, text: str) -> str:
        """Convert bullet points or list markers to spoken prose."""
        lines = text.split("\n")
        result: List[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Strip common list markers
            m = re.match(r"^[\-\*\•]\s+", line)
            if m:
                line = line[m.end() :].strip()
            m = re.match(r"^\d+[\.\)]\s+", line)
            if m:
                line = line[m.end() :].strip()
            if line:
                result.append(line)
        return " ".join(result) if result else text

    def _is_complex_topic(self, text: str, sentences: List[str]) -> bool:
        """Detect if response is explaining a complex topic (policy, process, multi-step)."""
        text_lower = text.lower()
        complex_markers = [
            "policy", "refund", "return", "procedure", "step", "first", "then",
            "however", "although", "required", "must", "need to", "ensure",
        ]
        if any(m in text_lower for m in complex_markers):
            return True
        # Longer responses with multiple sentences often indicate complexity
        return len(sentences) >= 3

    def _split_sentences(self, text: str) -> list:
        # Simple sentence split on ., !, ? while preserving abbreviations minimally
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    def _apply_nigerian_tone(self, text: str) -> str:
        # Replace overly formal phrases with natural Nigerian English equivalents (light touch)
        substitutions = {
            "I will": "I'll",
            "I have": "I've",
            # "Would you like"→"Do you want" handled selectively in _add_human_patterns (question context only)
            "No problem": "No wahala",
            "I understand": "I see what you mean",
            "That's correct": "Exactly",
            "Let me help": "I'd be happy to help",
            "Thank you": "Thanks",
            "You're welcome": "No wahala",
            "I'm sorry": "Sorry about that",
            "Please": "Kindly",
        }
        for k, v in substitutions.items():
            text = re.sub(rf"\b{k}\b", v, text, flags=re.IGNORECASE)
        return text

    def _contains_critical_detail(self, text: str) -> bool:
        # Heuristics: presence of numbers, times, dates, amounts
        if re.search(r"\b(\d{1,2}[:\.]?\d{0,2}\s?(am|pm))\b", text, flags=re.IGNORECASE):
            return True
        if re.search(r"\b(\d{1,2}\s?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))\b", text, flags=re.IGNORECASE):
            return True
        if re.search(r"\b(₦|Naira|NGN|\d{1,3}(,\d{3})*)(\.\d+)?\b", text, flags=re.IGNORECASE):
            return True
        if re.search(r"\b(street|road|close|avenue|island|lekki|ikeja|yaba)\b", text, flags=re.IGNORECASE):
            return True
        return False

    def _add_human_patterns(self, text: str, context: Dict[str, Any]) -> str:
        """Add human-like conversation patterns to make responses more natural."""
        # Add natural backchanneling for understanding (only when used as acknowledgment)
        # Replace "I see"/"I understand" only when followed by punctuation, not "I see the..."
        if any(word in text.lower() for word in ["understand", "see", "get it"]):
            text = re.sub(r"\bI understand([.,!?]|\s*$)", r"I see what you mean\1", text, flags=re.IGNORECASE)
            text = re.sub(r"\bI see([.,!?]|\s*$)", r"I see what you mean\1", text, flags=re.IGNORECASE)
        
        # Add natural transitions
        if text.startswith("Well,") or text.startswith("So,"):
            text = text.replace("Well,", "Alright,").replace("So,", "Okay,")
        
        # Add natural empathy phrases
        empathy_phrases = {
            "I'm sorry": "Sorry about that",
            "I apologize": "Sorry about that", 
            "That's unfortunate": "That's really unfortunate",
            "I understand your concern": "I completely understand your concern"
        }
        
        for formal, natural in empathy_phrases.items():
            text = text.replace(formal, natural)
        
        # Add natural question patterns
        if "?" in text:
            text = text.replace("Would you like", "Do you want")
            text = text.replace("Could you", "Can you")
        
        # Add natural closers
        if any(word in text.lower() for word in ["thank you", "thanks", "appreciate"]):
            text = text.replace("Thank you very much", "Thanks so much")
            text = text.replace("I appreciate", "I really appreciate")
        
        return text


