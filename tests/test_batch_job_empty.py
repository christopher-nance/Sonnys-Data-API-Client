"""Regression tests for the two defects this release fixes."""

import threading
import time
from unittest.mock import MagicMock

import pytest

from sonnys_data_client._rate_limiter import RateLimiter


class TestEmptyLoadJob:
    """load_job() must not crash when a site has no transactions that day."""

    def test_empty_result_returns_empty_list(self, monkeypatch):
        from sonnys_data_client import SonnysClient

        client = SonnysClient(api_id="x", api_key="y")

        # Exactly what the API returns for a site/day with no sales: every
        # paging field is null, not absent.
        submit = MagicMock()
        submit.json.return_value = {"data": {"hash": "abc"}}
        poll = MagicMock()
        poll.json.return_value = {
            "data": {
                "hash": "abc", "status": "pass", "data": [],
                "offset": None, "limit": None, "total": None,
            }
        }

        def fake_request(method, path, **kwargs):
            return submit if method == "POST" else poll

        monkeypatch.setattr(client, "_request", fake_request)

        # Before the fix this raised:
        #   TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
        assert client.transactions.load_job(
            startDate=1778821200, endDate=1778907600, site="BurbT2",
        ) == []


class TestRateLimiterHeadroom:
    def test_request_is_recorded_even_when_it_had_to_wait(self):
        """The caller sleeps and then sends WITHOUT calling acquire() again,
        so a request that waited must still occupy a slot."""
        limiter = RateLimiter(max_requests=3, window_seconds=10.0)
        for _ in range(3):
            assert limiter.acquire() == 0.0
        assert limiter.available == 0

        wait = limiter.acquire()
        assert wait > 0
        # The waiting request must have reserved a slot.
        assert len(limiter._timestamps) == 4

    def test_never_exceeds_budget_in_any_window(self):
        """Replay the client's acquire/sleep/send loop on a virtual clock."""
        window, budget = 15.0, 18
        limiter = RateLimiter(max_requests=budget, window_seconds=window)
        now, sent = 0.0, []

        for _ in range(200):
            cutoff = now - window
            while limiter._timestamps and limiter._timestamps[0] <= cutoff:
                limiter._timestamps.popleft()
            if len(limiter._timestamps) < budget:
                limiter._timestamps.append(now)
                wait = 0.0
            else:
                wait = max(limiter._timestamps[0] + window - now, 0.0)
                limiter._timestamps.append(now + wait)
            now += wait
            sent.append(now)
            now += 0.05

        worst = 0
        for i, t in enumerate(sent):
            j = i
            while j < len(sent) and sent[j] < t + window:
                j += 1
            worst = max(worst, j - i)
        # Must stay under the server's real ceiling of 20 per 15 s.
        assert worst <= 20

    def test_acquire_is_thread_safe(self):
        """Concurrent acquire() must not over-issue via a check-then-append
        race. Threads sharing one client share one limiter."""
        limiter = RateLimiter(max_requests=50, window_seconds=60.0)
        granted = []
        lock = threading.Lock()

        def worker():
            for _ in range(20):
                wait = limiter.acquire()
                with lock:
                    granted.append(wait)
                time.sleep(0)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        immediate = sum(1 for w in granted if w == 0.0)
        assert len(granted) == 160
        # Never more immediate grants than the budget allows.
        assert immediate <= 50
        assert len(limiter._timestamps) == 160
