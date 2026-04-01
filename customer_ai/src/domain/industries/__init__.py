"""Industry domain - taxonomy, config, and engines."""

from .taxonomy import (
    INDUSTRIES,
    INDUSTRY_ALIASES,
    resolve_industry,
    normalize_industry,
    is_valid_industry,
)

__all__ = [
    "INDUSTRIES",
    "INDUSTRY_ALIASES",
    "resolve_industry",
    "normalize_industry",
    "is_valid_industry",
]
