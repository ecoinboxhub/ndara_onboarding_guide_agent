"""
Canonical Industry Taxonomy for Customer AI
Single source of truth for industry identifiers across classifier, prompts, engines, and docs.
"""

from typing import List, Optional, Set

# Canonical industry keys used throughout the codebase
INDUSTRIES: List[str] = [
    "ecommerce",
    "healthcare",
    "real_estate",
    "restaurants",
    "education",
    "financial",
    "travel",
    "events",
    "logistics",
    "professional_services",
    "beauty_wellness",
    "telecoms",
    "banking",
    "manufacturing",
    "retail_chains",
]

# Mapping from docs/playbooks and legacy keys to canonical keys
INDUSTRY_ALIASES: dict = {
    # Niche playbook naming (docs/voice/niche_playbooks/)
    "ecommerce_retail": "ecommerce",
    "travel_hospitality": "travel",
    "events_entertainment": "events",
    "logistics_delivery": "logistics",
    "manufacturing_fmcg": "manufacturing",
    "enterprise_banking": "banking",
    "enterprise_telecoms": "telecoms",
    "restaurant": "restaurants",
    # Prompts module naming
    "financial_services": "financial",
    "finance": "financial",
}

# Valid industry set for fast lookup
_VALID_INDUSTRIES: Set[str] = set(INDUSTRIES)


def resolve_industry(industry: Optional[str]) -> Optional[str]:
    """
    Resolve any industry alias or variant to the canonical key.
    Returns None if input is None or empty.
    """
    if not industry or not isinstance(industry, str):
        return None
    key = industry.strip().lower()
    if not key:
        return None
    # First check aliases (docs/playbooks, legacy keys)
    canonical = INDUSTRY_ALIASES.get(key)
    if canonical:
        return canonical
    # Already canonical
    if key in _VALID_INDUSTRIES:
        return key
    return None


def normalize_industry(industry: Optional[str]) -> str:
    """
    Normalize industry to canonical key. Falls back to 'general' if unknown.
    Use when a non-optional industry is required.
    """
    resolved = resolve_industry(industry)
    if resolved and resolved in _VALID_INDUSTRIES:
        return resolved
    return "general"


def is_valid_industry(industry: Optional[str]) -> bool:
    """Check if the given industry (after resolution) is a valid canonical industry."""
    resolved = resolve_industry(industry)
    return resolved is not None and resolved in _VALID_INDUSTRIES


def get_all_industries() -> List[str]:
    """Return list of all canonical industry keys."""
    return list(INDUSTRIES)
