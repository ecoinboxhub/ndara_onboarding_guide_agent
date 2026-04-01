"""
Call-type-aware greeting (first utterance) for inbound and outbound calls.
For every call, the introduction should be played first; content differs by call_type and outbound reason.
"""

from typing import Optional

# Outbound reason -> friendly phrase for the first line (e.g. "calling about your cart")
OUTBOUND_REASON_PHRASES = {
    "abandoned_cart": "items left in your cart",
    "order_issues": "your recent order",
    "technical_fixed": "the technical issue we resolved",
    "promotional": "a special offer for you",
    "coupons": "coupons and bonuses you might like",
    "bonuses": "bonuses we have for you",
    "follow_up": "a quick follow-up",
    "reminder": "a reminder",
    "survey": "a short survey",
}


def get_greeting_text(
    call_type: str,
    business_name: str,
    reason: Optional[str] = None,
) -> str:
    """
    Return the first-utterance text for a call. Play this before any user audio.

    - Inbound: welcome + business name + "How may I help you today?"
    - Outbound: business name + optional reason + "How can we help you today?"

    Args:
        call_type: "inbound" | "outbound"
        business_name: Display name of the business (from onboarding). Required; do not use business_id.
        reason: For outbound only. Canonical: abandoned_cart, order_issues, technical_fixed,
                promotional, coupons, bonuses, follow_up, reminder, survey. Or free-form string.

    Raises:
        ValueError: If business_name is missing or empty (must be provisioned from onboarding).
    """
    if not (business_name and business_name.strip()):
        raise ValueError("business_name is required for greeting (provision from onboarding)")
    name = business_name.strip()
    call_type_val = (call_type or "inbound").strip().lower()
    reason_phrase = None
    if reason and call_type_val == "outbound":
        reason_phrase = OUTBOUND_REASON_PHRASES.get(
            reason.strip().lower(), reason.strip()
        )

    if call_type_val == "outbound":
        if reason_phrase:
            return f"Good day, this is {name} calling about {reason_phrase}. How can we help you today?"
        return f"Good day, this is {name} calling. How can we help you today?"
    # inbound (default)
    return f"Good day, you've reached {name}. How may I help you today?"
