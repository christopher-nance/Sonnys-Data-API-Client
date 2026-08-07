"""Sliding window rate limiter for the Sonny's Data API."""

from __future__ import annotations

import threading
import time
from collections import deque


class RateLimiter:
    """Per-instance sliding window rate limiter.

    Tracks request timestamps in a :class:`~collections.deque` and enforces a
    maximum number of requests within a rolling time window.  The limiter does
    **not** sleep -- :meth:`acquire` returns the wait duration so the caller
    can decide how to handle throttling.

    Args:
        max_requests: Maximum requests allowed per window (default 20).
        window_seconds: Length of the sliding window in seconds (default 15.0).
    """

    def __init__(
        self,
        max_requests: int = 18,
        window_seconds: float = 15.0,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _purge(self, now: float) -> None:
        """Remove timestamps that have fallen outside the sliding window."""
        cutoff = now - self._window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self) -> float:
        """Record a request and return the wait time before it can proceed.

        Returns:
            ``0.0`` if the request is within the rate limit, or a positive
            float representing the number of seconds the caller should wait
            before retrying.
        """
        with self._lock:
            now = time.monotonic()
            self._purge(now)

            if len(self._timestamps) < self._max_requests:
                self._timestamps.append(now)
                return 0.0

            # At capacity -- calculate how long until the oldest entry expires.
            wait = self._timestamps[0] + self._window_seconds - now
            wait = max(wait, 0.0)
            # Record the request at the moment it will actually be sent. The
            # caller sleeps for `wait` and then sends without calling acquire()
            # again, so without this the request is never counted and the
            # window drifts over budget.
            self._timestamps.append(now + wait)
            return wait

    def reset(self) -> None:
        """Clear all recorded timestamps."""
        with self._lock:
            self._timestamps.clear()

    @property
    def available(self) -> int:
        """Number of requests available in the current window."""
        with self._lock:
            now = time.monotonic()
            self._purge(now)
            return self._max_requests - len(self._timestamps)


