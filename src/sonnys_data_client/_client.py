"""Core client for the Sonny's Carwash Controls Data API."""

from __future__ import annotations

import functools
import logging
import time
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger("sonnys_data_client")

from sonnys_data_client._exceptions import (
    APIConnectionError,
    APITimeoutError,
    make_status_error,
)
from sonnys_data_client._rate_limiter import RateLimiter
from sonnys_data_client.resources._customers import Customers
from sonnys_data_client.resources._employees import Employees
from sonnys_data_client.resources._giftcards import Giftcards
from sonnys_data_client.resources._items import Items
from sonnys_data_client.resources._recurring import RecurringAccounts
from sonnys_data_client.resources._sites import Sites
from sonnys_data_client.resources._stats import StatsResource
from sonnys_data_client.resources._transactions import Transactions
from sonnys_data_client.resources._washbooks import Washbooks


class SonnysClient:
    """Client for the Sonny's Carwash Controls Data API.

    Manages authentication and HTTP session lifecycle. Use as a context
    manager or call :meth:`close` explicitly when done.

    Args:
        api_id: Sonny's API ID credential.
        api_key: Sonny's API key credential.
        site_code: Optional site code to scope requests to a specific site.
        max_retries: Maximum number of retries for 429 responses.
    """

    BASE_URL = "https://trigonapi.sonnyscontrols.com/v1"

    def __init__(
        self,
        api_id: str,
        api_key: str,
        site_code: str | None = None,
        *,
        max_retries: int = 3,
    ) -> None:
        self.api_id = api_id
        self.api_key = api_key
        self.site_code = site_code
        self._max_retries = max_retries
        self._rate_limiter = RateLimiter()

        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-Sonnys-API-ID": api_id,
                "X-Sonnys-API-Key": api_key,
            }
        )
        if site_code is not None:
            self._session.headers["X-Sonnys-Site-Code"] = site_code

    @functools.cached_property
    def site_timezone(self) -> ZoneInfo | None:
        """Look up the IANA timezone for the configured site.

        Returns ``None`` if no ``site_code`` was provided (UTC fallback).
        Cached for the client lifetime (one ``/sites`` API call max).

        Raises:
            ValueError: If ``site_code`` doesn't match any site.
        """
        if self.site_code is None:
            return None
        for site in self.sites.list():
            if site.code == self.site_code:
                return ZoneInfo(site.timezone) if site.timezone else None
        raise ValueError(f"Site code {self.site_code!r} not found in sites list")

    @functools.cached_property
    def customers(self) -> Customers:
        """Access the Customers resource."""
        return Customers(self)

    @functools.cached_property
    def items(self) -> Items:
        """Access the Items resource."""
        return Items(self)

    @functools.cached_property
    def employees(self) -> Employees:
        """Access the Employees resource."""
        return Employees(self)

    @functools.cached_property
    def giftcards(self) -> Giftcards:
        """Access the Giftcards resource."""
        return Giftcards(self)

    @functools.cached_property
    def sites(self) -> Sites:
        """Access the Sites resource."""
        return Sites(self)

    @functools.cached_property
    def stats(self) -> StatsResource:
        """Access the Stats resource for business analytics."""
        return StatsResource(self)

    @functools.cached_property
    def transactions(self) -> Transactions:
        """Access the Transactions resource."""
        return Transactions(self)

    @functools.cached_property
    def washbooks(self) -> Washbooks:
        """Access the Washbooks resource."""
        return Washbooks(self)

    @functools.cached_property
    def recurring(self) -> RecurringAccounts:
        """Access the Recurring Accounts resource."""
        return RecurringAccounts(self)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
    ) -> requests.Response:
        """Send an HTTP request with rate limiting and 429 retry.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: URL path appended to :attr:`BASE_URL`.
            params: Optional query parameters forwarded to the request.

        Returns:
            The HTTP response when the status code is < 400.

        Raises:
            APIConnectionError: On connection failure.
            APITimeoutError: On request timeout.
            RateLimitError: When 429 retries are exhausted.
            APIStatusError: On other HTTP error status codes.
        """
        for attempt in range(self._max_retries + 1):
            # Step 1: Rate limit check
            wait = self._rate_limiter.acquire()
            if wait > 0:
                logger.debug("Rate limiter: waiting %.3fs", wait)
                time.sleep(wait)

            # Step 2: Send request
            logger.debug("Request: %s %s params=%s", method, path, params)
            try:
                response = self._session.request(
                    method,
                    self.BASE_URL + path,
                    params=params,
                )
            except requests.ConnectionError:
                raise APIConnectionError()
            except requests.Timeout:
                raise APITimeoutError()

            # Step 4: Handle success
            if response.status_code < 400:
                logger.debug(
                    "Response: %s %s status=%d elapsed=%.3fs",
                    method, path, response.status_code,
                    response.elapsed.total_seconds(),
                )
                return response

            # Step 5: Log error response details
            logger.debug(
                "Error response: %s %s status=%d body=%s",
                method, path, response.status_code, response.text,
            )

            # Step 6: Handle 429
            if response.status_code == 429:
                if attempt < self._max_retries:
                    delay = 2.0 * (attempt + 1)
                    logger.warning(
                        "Rate limited (429), retry %d/%d after %.1fs",
                        attempt + 1, self._max_retries, delay,
                    )
                    time.sleep(delay)
                    continue
                raise make_status_error(response)

            # Step 7: Handle other errors
            raise make_status_error(response)

        # Should never reach here, but satisfy type checker
        raise make_status_error(response)  # pragma: no cover

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self) -> SonnysClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"SonnysClient(base_url='{self.BASE_URL}')"
