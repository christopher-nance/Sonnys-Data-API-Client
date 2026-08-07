"""Tests for the sliding window rate limiter."""

from unittest.mock import patch

from sonnys_data_client._rate_limiter import RateLimiter


# ---------------------------------------------------------------------------
# Constructor defaults and custom values
# ---------------------------------------------------------------------------


class TestRateLimiterConstructor:
    """Tests for RateLimiter constructor configuration."""

    def test_defaults(self) -> None:
        """Default constructor uses 18 requests per 15-second window.

        The server allows exactly 20 per 15s. Targeting 20 leaves no margin
        for clock skew or network jitter, which made 429s routine in sustained
        batch use; 18 keeps deliberate headroom.
        """
        limiter = RateLimiter()

        assert limiter._max_requests == 18
        assert limiter._window_seconds == 15.0

    def test_custom_values(self) -> None:
        """Custom max_requests and window_seconds are stored correctly."""
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        assert limiter._max_requests == 3
        assert limiter._window_seconds == 1.0


# ---------------------------------------------------------------------------
# acquire() behavior
# ---------------------------------------------------------------------------


class TestAcquire:
    """Tests for RateLimiter.acquire() request tracking."""

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_under_limit_returns_zero(self, mock_monotonic) -> None:
        """acquire() returns 0.0 when under the request limit."""
        mock_monotonic.return_value = 100.0
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        wait = limiter.acquire()

        assert wait == 0.0

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_exactly_at_limit_returns_zero(self, mock_monotonic) -> None:
        """acquire() returns 0.0 for exactly max_requests calls (boundary)."""
        mock_monotonic.return_value = 100.0
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        # All 3 calls should succeed
        assert limiter.acquire() == 0.0
        assert limiter.acquire() == 0.0
        assert limiter.acquire() == 0.0

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_over_limit_returns_positive_wait(self, mock_monotonic) -> None:
        """acquire() returns positive float when at limit (4th call with max_requests=3)."""
        mock_monotonic.return_value = 100.0
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        # Fill the window
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()

        # 4th call should return positive wait time
        wait = limiter.acquire()

        assert wait > 0.0

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_over_limit_wait_equals_time_until_oldest_exits(self, mock_monotonic) -> None:
        """Wait time should be the time until the oldest timestamp exits the window."""
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        # Fill window at different times
        mock_monotonic.return_value = 100.0
        limiter.acquire()
        mock_monotonic.return_value = 100.3
        limiter.acquire()
        mock_monotonic.return_value = 100.6
        limiter.acquire()

        # 4th call at t=100.8 — oldest (100.0) exits at t=101.0, wait = 0.2
        mock_monotonic.return_value = 100.8
        wait = limiter.acquire()

        assert abs(wait - 0.2) < 1e-9

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_window_slides_after_time_elapses(self, mock_monotonic) -> None:
        """After window elapses, acquire() returns 0.0 again."""
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        # Fill window at t=100.0
        mock_monotonic.return_value = 100.0
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()

        # Jump to t=101.1 — all timestamps older than 100.1 are purged
        mock_monotonic.return_value = 101.1
        wait = limiter.acquire()

        assert wait == 0.0

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_partial_window_slide(self, mock_monotonic) -> None:
        """After some timestamps expire, only those are purged."""
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        # Fill window at different times
        mock_monotonic.return_value = 100.0
        limiter.acquire()
        mock_monotonic.return_value = 100.5
        limiter.acquire()
        mock_monotonic.return_value = 100.8
        limiter.acquire()

        # At t=101.1, only first (100.0) has expired; 2 remain, 1 available
        mock_monotonic.return_value = 101.1
        wait = limiter.acquire()

        assert wait == 0.0

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_default_limit_19th_call_returns_positive(self, mock_monotonic) -> None:
        """With default settings, the 19th call returns a positive wait."""
        mock_monotonic.return_value = 100.0
        limiter = RateLimiter()  # 18 req / 15s, headroom under the server's 20

        # 18 calls should all succeed
        for _ in range(18):
            assert limiter.acquire() == 0.0

        # 21st should return positive wait
        wait = limiter.acquire()

        assert wait > 0.0


# ---------------------------------------------------------------------------
# reset() behavior
# ---------------------------------------------------------------------------


class TestReset:
    """Tests for RateLimiter.reset()."""

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_reset_clears_state(self, mock_monotonic) -> None:
        """After reset(), acquire() returns 0.0 even if previously at limit."""
        mock_monotonic.return_value = 100.0
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        # Fill the window
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()

        # At limit — 4th would wait
        wait = limiter.acquire()
        assert wait > 0.0

        # Reset and try again
        limiter.reset()
        wait = limiter.acquire()

        assert wait == 0.0


# ---------------------------------------------------------------------------
# available property
# ---------------------------------------------------------------------------


class TestAvailable:
    """Tests for RateLimiter.available property."""

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_available_starts_at_max(self, mock_monotonic) -> None:
        """available starts at max_requests when no requests have been made."""
        mock_monotonic.return_value = 100.0
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        assert limiter.available == 3

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_available_decreases_after_acquire(self, mock_monotonic) -> None:
        """available decreases by 1 after each successful acquire()."""
        mock_monotonic.return_value = 100.0
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        limiter.acquire()
        assert limiter.available == 2

        limiter.acquire()
        assert limiter.available == 1

        limiter.acquire()
        assert limiter.available == 0

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_available_recovers_after_window_slides(self, mock_monotonic) -> None:
        """available recovers when timestamps expire from the window."""
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        mock_monotonic.return_value = 100.0
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()

        assert limiter.available == 0

        # Jump past window
        mock_monotonic.return_value = 101.1
        assert limiter.available == 3

    @patch("sonnys_data_client._rate_limiter.time.monotonic")
    def test_available_after_reset(self, mock_monotonic) -> None:
        """available returns max_requests after reset()."""
        mock_monotonic.return_value = 100.0
        limiter = RateLimiter(max_requests=3, window_seconds=1.0)

        limiter.acquire()
        limiter.acquire()
        assert limiter.available == 1

        limiter.reset()
        assert limiter.available == 3
