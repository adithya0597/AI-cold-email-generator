"""
Tests for Story 0.6: Exponential backoff retry utility.

Validates:
  AC#4 - Exponential backoff with base_delay * 2^attempt, capped at max_delay
"""

from app.worker.retry import calculate_backoff


# ============================================================
# AC#4 - Exponential Backoff Calculation
# ============================================================


class TestCalculateBackoff:
    """AC#4: Backoff grows exponentially and caps at max_delay."""

    def test_calculate_backoff_attempt_0(self):
        """Attempt 0: 30 * 2^0 = 30."""
        assert calculate_backoff(0) == 30

    def test_calculate_backoff_attempt_1(self):
        """Attempt 1: 30 * 2^1 = 60."""
        assert calculate_backoff(1) == 60

    def test_calculate_backoff_attempt_2(self):
        """Attempt 2: 30 * 2^2 = 120."""
        assert calculate_backoff(2) == 120

    def test_calculate_backoff_attempt_3(self):
        """Attempt 3: 30 * 2^3 = 240."""
        assert calculate_backoff(3) == 240

    def test_calculate_backoff_attempt_4(self):
        """Attempt 4: 30 * 2^4 = 480."""
        assert calculate_backoff(4) == 480

    def test_calculate_backoff_max_cap(self):
        """Large attempt numbers cap at max_delay (600)."""
        assert calculate_backoff(10) == 600
        assert calculate_backoff(20) == 600

    def test_calculate_backoff_custom_base(self):
        """Custom base_delay is respected."""
        assert calculate_backoff(0, base_delay=10) == 10
        assert calculate_backoff(1, base_delay=10) == 20
        assert calculate_backoff(2, base_delay=10) == 40

    def test_calculate_backoff_custom_max(self):
        """Custom max_delay caps correctly."""
        assert calculate_backoff(5, base_delay=30, max_delay=100) == 100
