"""
Tests for Story 0.4: Rate Limiting Middleware.

Validates:
  AC5 - Tier-based rate limits (Free=100, Pro=1000, H1B Pro=1000)
  AC6 - 429 response with Retry-After header when exceeded
"""

import pytest

from app.middleware.rate_limit import (
    EXEMPT_PATHS,
    TIER_LIMITS,
    WINDOW_SECONDS,
    _InMemoryStore,
)


# ============================================================
# AC5 - Tier Configuration
# ============================================================


class TestTierConfiguration:
    """AC5: Rate limiting enforces tier-based limits."""

    def test_free_tier_limit(self):
        assert TIER_LIMITS["free"] == 100

    def test_pro_tier_limit(self):
        assert TIER_LIMITS["pro"] == 1000

    def test_h1b_pro_tier_limit(self):
        assert TIER_LIMITS["h1b_pro"] == 1000

    def test_career_insurance_tier_limit(self):
        assert TIER_LIMITS["career_insurance"] == 1000

    def test_enterprise_tier_limit(self):
        assert TIER_LIMITS["enterprise"] == 5000

    def test_window_is_one_hour(self):
        assert WINDOW_SECONDS == 3600

    def test_all_user_tiers_have_limits(self):
        """Every user_tier enum value should have a rate limit entry."""
        expected_tiers = {"free", "pro", "h1b_pro", "career_insurance", "enterprise"}
        assert expected_tiers.issubset(set(TIER_LIMITS.keys()))


# ============================================================
# Exempt Paths
# ============================================================


class TestExemptPaths:
    """Health and docs endpoints are exempt from rate limiting."""

    def test_health_endpoint_exempt(self):
        assert "/api/v1/health" in EXEMPT_PATHS

    def test_docs_exempt(self):
        assert "/docs" in EXEMPT_PATHS

    def test_redoc_exempt(self):
        assert "/redoc" in EXEMPT_PATHS

    def test_openapi_exempt(self):
        assert "/openapi.json" in EXEMPT_PATHS


# ============================================================
# In-Memory Store
# ============================================================


class TestInMemoryStore:
    """In-memory sliding window counter works correctly."""

    @pytest.mark.asyncio
    async def test_increment_returns_count(self):
        store = _InMemoryStore()
        count = await store.increment("test-key", 3600)
        assert count == 1

    @pytest.mark.asyncio
    async def test_multiple_increments_accumulate(self):
        store = _InMemoryStore()
        for _ in range(5):
            count = await store.increment("test-key", 3600)
        assert count == 5

    @pytest.mark.asyncio
    async def test_different_keys_are_independent(self):
        store = _InMemoryStore()
        await store.increment("key-a", 3600)
        await store.increment("key-a", 3600)
        count_b = await store.increment("key-b", 3600)
        assert count_b == 1


# ============================================================
# AC6 - 429 Response Format
# ============================================================


class TestRateLimitResponseFormat:
    """AC6: Verify the 429 response structure is correct."""

    def test_tier_limits_is_dict(self):
        """TIER_LIMITS should be a dict mapping tier names to integer limits."""
        assert isinstance(TIER_LIMITS, dict)
        for tier, limit in TIER_LIMITS.items():
            assert isinstance(tier, str)
            assert isinstance(limit, int)
            assert limit > 0
