"""Unit tests for industry taxonomy."""

import pytest
from src.domain.industries.taxonomy import (
    INDUSTRIES,
    resolve_industry,
    normalize_industry,
    is_valid_industry,
    get_all_industries,
)


class TestResolveIndustry:
    """Tests for resolve_industry."""

    def test_canonical_returns_self(self):
        assert resolve_industry("ecommerce") == "ecommerce"
        assert resolve_industry("healthcare") == "healthcare"

    def test_alias_from_playbooks(self):
        assert resolve_industry("ecommerce_retail") == "ecommerce"
        assert resolve_industry("travel_hospitality") == "travel"
        assert resolve_industry("financial_services") == "financial"
        assert resolve_industry("restaurant") == "restaurants"

    def test_case_insensitive(self):
        assert resolve_industry("Ecommerce") == "ecommerce"
        assert resolve_industry("HEALTHCARE") == "healthcare"

    def test_none_empty(self):
        assert resolve_industry(None) is None
        assert resolve_industry("") is None
        assert resolve_industry("   ") is None

    def test_unknown_returns_none(self):
        assert resolve_industry("unknown_vertical") is None


class TestNormalizeIndustry:
    """Tests for normalize_industry."""

    def test_valid_returns_canonical(self):
        assert normalize_industry("ecommerce") == "ecommerce"
        assert normalize_industry("travel_hospitality") == "travel"

    def test_unknown_falls_back_to_general(self):
        assert normalize_industry("unknown") == "general"
        assert normalize_industry(None) == "general"


class TestIsValidIndustry:
    """Tests for is_valid_industry."""

    def test_valid_canonical(self):
        assert is_valid_industry("ecommerce") is True

    def test_valid_alias_resolves(self):
        assert is_valid_industry("ecommerce_retail") is True

    def test_invalid(self):
        assert is_valid_industry("unknown") is False
        assert is_valid_industry(None) is False


class TestGetAllIndustries:
    """Tests for get_all_industries."""

    def test_returns_fifteen(self):
        industries = get_all_industries()
        assert len(industries) == 15
        assert "ecommerce" in industries
        assert "healthcare" in industries
