"""Transactions resource."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sonnys_data_client._exceptions import APIError, APITimeoutError

logger = logging.getLogger("sonnys_data_client")
from sonnys_data_client._resources import GettableResource, ListableResource
from sonnys_data_client.types._base import SonnysModel
from sonnys_data_client.types._transactions import (
    Transaction,
    TransactionJobItem,
    TransactionListItem,
    TransactionV2ListItem,
)


class Transactions(ListableResource, GettableResource):
    """Access the /transaction list, detail, and by-type endpoints.

    The most complex resource, providing paginated transaction search,
    individual transaction lookup, type-filtered listing, and batch job
    support for large exports.

    - ``list()`` returns :class:`~sonnys_data_client.types.TransactionListItem`
      summaries. Supports ``startDate``, ``endDate``, ``site``, ``region``
      filters.
    - ``get(id)`` returns a full :class:`~sonnys_data_client.types.Transaction`
      record with line items, tenders, and discounts.
    - ``list_by_type(type)`` filters transactions by type (wash, recurring, etc.).
    - ``list_v2()`` uses the enriched v2 endpoint with customer and status fields.
    - ``load_job()`` submits asynchronous batch jobs for large date ranges.
    """

    _path = "/transaction"
    _items_key = "transactions"
    _model = TransactionListItem
    _default_limit = 100
    _paginated = True

    _detail_path = "/transaction/{id}"
    _detail_model = Transaction

    @staticmethod
    def _convert_dates(params: dict) -> dict:
        """Convert ISO date strings to Unix timestamps for the API.

        The Sonny's API expects ``startDate`` and ``endDate`` as integer
        Unix timestamps.  This helper lets callers pass human-readable
        ISO-8601 strings (e.g. ``"2026-01-15"``) which are converted
        automatically.  Values that are already numeric pass through
        unchanged.
        """
        converted = dict(params)
        for key in ("startDate", "endDate"):
            value = converted.get(key)
            if value is None or isinstance(value, (int, float)):
                continue
            if isinstance(value, str):
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                converted[key] = int(dt.timestamp())
        # Validate 1-month max range
        start_ts = converted.get("startDate")
        end_ts = converted.get("endDate")
        if start_ts is not None and end_ts is not None:
            days = (int(end_ts) - int(start_ts)) / 86400
            if days > 31:
                raise ValueError(
                    f"Date range cannot exceed 31 days (got {int(days)} days). "
                    "The Sonny's API requires startDate and endDate to be "
                    "within 1 month of each other."
                )
        return converted

    def list(self, **params: object) -> list[TransactionListItem]:
        """Fetch all transactions, converting date strings to timestamps.

        Accepts ``startDate`` / ``endDate`` as ISO-8601 strings
        (e.g. ``"2026-01-15"``) or Unix timestamps.

        Returns:
            A flat list of :class:`TransactionListItem` instances.
        """
        return super().list(**self._convert_dates(params))

    def _paginated_fetch(
        self,
        path: str,
        items_key: str,
        model: type[SonnysModel],
        limit: int = 100,
        **params: object,
    ) -> list[SonnysModel]:
        """Fetch all pages from a paginated endpoint.

        Generic pagination helper used by the custom list methods to avoid
        duplicating the offset-based pagination loop.

        Args:
            path: API endpoint path.
            items_key: Key inside ``data`` that holds the items array.
            model: Pydantic model class to validate each item against.
            limit: Page size for paginated requests.
            **params: Extra query parameters forwarded to every request.

        Returns:
            A list of validated Pydantic model instances.
        """
        all_items: list[SonnysModel] = []
        page = 1

        while True:
            request_params = {
                "limit": limit,
                "offset": page,
                **params,
            }
            response = self._client._request("GET", path, params=request_params)
            data = response.json()["data"]

            items = data[items_key]
            total = data.get("total")

            for item in items:
                all_items.append(model.model_validate(item))

            if len(items) < limit:
                break
            page += 1
            if total is not None and len(all_items) >= total:
                break

        return all_items

    def list_by_type(self, item_type: str, **params: object) -> list[TransactionListItem]:
        """Fetch all transactions of a specific type.

        Valid types include: wash, prepaid-wash, recurring, washbook,
        giftcard, merchandise, house-account. The API validates the type
        parameter.

        Args:
            item_type: The transaction type to filter by.
            **params: Extra query parameters forwarded to every request
                (e.g., ``startDate``, ``endDate``, ``site``, ``region``).

        Returns:
            A flat list of :class:`TransactionListItem` instances.
        """
        return self._paginated_fetch(
            f"/transaction/type/{item_type}",
            "transactions",
            TransactionListItem,
            **self._convert_dates(params),
        )

    def list_v2(self, **params: object) -> list[TransactionV2ListItem]:
        """Fetch all transactions using the v2 endpoint.

        The v2 endpoint returns enriched list items with ``customer_id``,
        ``is_recurring_plan_sale``, ``is_recurring_plan_redemption``, and
        ``transaction_status`` fields.

        Note: The API caches v2 responses for 10 minutes per reporting criteria.

        Returns:
            A flat list of :class:`TransactionV2ListItem` instances.
        """
        return self._paginated_fetch(
            "/transaction/version-2",
            "transactions",
            TransactionV2ListItem,
            **self._convert_dates(params),
        )

    def _submit_and_poll(
        self,
        *,
        poll_interval: float,
        timeout: float,
        **params: object,
    ) -> tuple[list[dict], int]:
        """Submit a single load-job page and poll until results are ready.

        Returns:
            A tuple of (list of raw item dicts, total count).
        """
        logger.debug("Job submit: POST /transaction/load-job params=%s", params)
        response = self._client._request(
            "POST", "/transaction/load-job", params=params,
        )
        hash_value = response.json()["data"]["hash"]
        logger.debug("Job submitted: hash=%s", hash_value)

        deadline = time.monotonic() + timeout
        poll_count = 0
        while True:
            poll_count += 1
            logger.debug("Job poll #%d: hash=%s", poll_count, hash_value)
            response = self._client._request(
                "GET",
                "/transaction/get-job-data",
                params={"hash": hash_value},
            )
            body = response.json()["data"]
            status = body["status"]

            if status == "pass":
                # An empty result comes back as
                # {"status": "pass", "offset": null, "limit": null,
                #  "total": null} — dict.get's default does NOT apply when the
                # key is present and null, so fall back explicitly. Without
                # this, load_job() raises TypeError on any site/day with no
                # transactions.
                total = body.get("total")
                if total is None:
                    total = len(body["data"])
                logger.debug(
                    "Job complete: hash=%s records=%d polls=%d",
                    hash_value, total, poll_count,
                )
                return body["data"], total

            if status == "fail":
                logger.error("Job failed: hash=%s", hash_value)
                raise APIError("Batch job failed")

            if time.monotonic() >= deadline:
                raise APITimeoutError(
                    f"Batch job did not complete within {timeout}s"
                )

            logger.debug("Job pending: hash=%s status=%s", hash_value, status)
            time.sleep(poll_interval)

    def load_job(
        self,
        *,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
        **params: object,
    ) -> list[TransactionJobItem]:
        """Submit batch jobs and auto-paginate through all results.

        Pagination happens at the job submission level: each call to
        ``/transaction/load-job`` with a different ``offset`` fetches
        one page. The method submits as many jobs as needed to retrieve
        all records.

        Note: The API caches job data for 20 minutes and limits the date
        range to a maximum of 24 hours.

        Args:
            poll_interval: Seconds between poll attempts (default 2.0).
            timeout: Max seconds to wait for each job (default 300.0).
            **params: Query parameters (``startDate``, ``endDate``,
                ``site``, ``limit``, ``offset``, etc.).

        Returns:
            A list of :class:`TransactionJobItem` instances.

        Raises:
            APIError: If any job status is ``"fail"``.
            APITimeoutError: If any job does not complete within *timeout*.
        """
        params = self._convert_dates(params)
        limit = int(params.get("limit", 100))
        page = int(params.get("offset", 1))

        # First page
        items, total = self._submit_and_poll(
            poll_interval=poll_interval,
            timeout=timeout,
            **{**params, "limit": limit, "offset": page},
        )
        all_items = [TransactionJobItem.model_validate(i) for i in items]

        # Remaining pages
        total_pages = (total + limit - 1) // limit
        page += 1
        while page <= total_pages:
            items, _ = self._submit_and_poll(
                poll_interval=poll_interval,
                timeout=timeout,
                **{**params, "limit": limit, "offset": page},
            )
            for i in items:
                all_items.append(TransactionJobItem.model_validate(i))
            page += 1

        return all_items
