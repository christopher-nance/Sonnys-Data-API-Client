"""Stats resource for business analytics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sonnys_data_client._date_utils import build_date_chunks, parse_date_range
from sonnys_data_client._resources import BaseResource
from sonnys_data_client.types._employees import ClockEntry
from sonnys_data_client.types._recurring import RecurringStatusChange
from sonnys_data_client.types._stats import ConversionResult, SalesResult, StatsReport, WashResult
from sonnys_data_client.types._transactions import (
    TransactionListItem,
    TransactionV2ListItem,
)

if TYPE_CHECKING:
    from sonnys_data_client._client import SonnysClient


class StatsResource(BaseResource):
    """Access computed business analytics and KPIs.

    Unlike other resources that wrap REST endpoints directly,
    ``StatsResource`` computes analytics by fetching raw data and
    aggregating it locally.  Individual stat methods (total sales,
    total washes, conversion rate, etc.) will be added in Phases 21-25.

    All stat methods accept a date range and delegate to
    :meth:`_resolve_dates` for consistent parsing and validation.
    """

    def __init__(self, client: SonnysClient) -> None:
        super().__init__(client)

    def _resolve_dates(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> dict[str, int]:
        """Validate a date range and convert to Unix timestamp parameters.

        Delegates to :func:`~sonnys_data_client._date_utils.parse_date_range`
        for parsing and validation, then converts the resulting datetimes to
        integer Unix timestamps suitable for API query parameters.

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            A dict with ``startDate`` and ``endDate`` keys whose values are
            Unix timestamps (int), ready to pass as query parameters.

        Raises:
            ValueError: If *start* is after *end*, or if a string cannot
                be parsed as a valid ISO-8601 date/datetime.
        """
        tz = self._client.site_timezone
        start_dt, end_dt = parse_date_range(start, end, tz=tz)
        # Cap end_dt at current time — the API rejects future timestamps
        # (timezone conversion can push end-of-day past midnight UTC)
        now = datetime.now(timezone.utc)
        if end_dt > now:
            end_dt = now
        return {
            "startDate": int(start_dt.timestamp()),
            "endDate": int(end_dt.timestamp()),
        }

    def _fetch_transactions(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> list[TransactionListItem]:
        """Fetch all transactions within a date range.

        Delegates to :meth:`~sonnys_data_client.resources.Transactions.list`
        after converting the date range to Unix timestamp query parameters.

        Used by stat methods that need the full transaction list (e.g.
        total sales as the sum of transaction totals).

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            A list of :class:`TransactionListItem` instances for the range.
        """
        return self._client.transactions.list(**self._resolve_dates(start, end))

    def _fetch_transactions_by_type(
        self,
        start: str | datetime,
        end: str | datetime,
        item_type: str,
    ) -> list[TransactionListItem]:
        """Fetch all transactions of a specific type within a date range.

        Delegates to
        :meth:`~sonnys_data_client.resources.Transactions.list_by_type`
        after converting the date range to Unix timestamp query parameters.

        Used by stat methods that need type-filtered transactions (e.g.
        total washes, retail wash count).

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.
            item_type: The transaction type to filter by (e.g. ``"wash"``,
                ``"recurring"``, ``"prepaid-wash"``).

        Returns:
            A list of :class:`TransactionListItem` instances matching the
            given type within the range.
        """
        return self._client.transactions.list_by_type(
            item_type, **self._resolve_dates(start, end)
        )

    def _fetch_transactions_v2(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> list[TransactionV2ListItem]:
        """Fetch all transactions using the enriched v2 endpoint.

        Delegates to
        :meth:`~sonnys_data_client.resources.Transactions.list_v2`
        after converting the date range to Unix timestamp query parameters.

        The v2 endpoint returns enriched records with
        ``is_recurring_plan_sale``, ``is_recurring_plan_redemption``, and
        ``transaction_status`` fields, enabling single-fetch efficiency for
        stat methods that need to classify transactions by multiple criteria
        (e.g. the full report method).

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            A list of :class:`TransactionV2ListItem` instances for the range.
        """
        return self._client.transactions.list_v2(**self._resolve_dates(start, end))

    def _fetch_recurring_status_changes(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> list[RecurringStatusChange]:
        """Fetch recurring account status change events within a date range.

        Delegates to
        :meth:`~sonnys_data_client.resources.RecurringAccounts.list_status_changes`
        after converting the date range to Unix timestamp query parameters.

        Each status change records a transition from ``old_status`` to
        ``new_status`` along with the date, employee, and site where the
        change occurred.  Used by stat methods that analyse membership
        activity (e.g. new memberships sold by filtering for activation
        transitions).

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            A list of :class:`RecurringStatusChange` instances for the range.
        """
        return self._client.recurring.list_status_changes(
            **self._resolve_dates(start, end)
        )

    def _fetch_all_clock_entries(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> list[ClockEntry]:
        """Bulk-fetch clock entries across all employees for a date range.

        Iterates every employee returned by ``employees.list()`` and
        fetches their clock entries in 14-day windows (the API's hard
        maximum per request).  All results are collected into a single
        flat list and optionally filtered to only the entries matching
        ``self._client.site_code``.

        **API cost:** 1 call (employee list) +
        N_employees x ceil(days / 14) calls (clock entries).

        Site-code filtering is applied locally after fetching, because
        the clock-entries endpoint does not support a site filter.

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            A flat list of :class:`ClockEntry` instances for the range.
        """
        # --- Resolve to YYYY-MM-DD strings (no timezone conversion) ---
        start_str = start.isoformat()[:10] if isinstance(start, datetime) else start
        if "T" in start_str:
            start_str = start_str.split("T")[0]
        end_str = end.isoformat()[:10] if isinstance(end, datetime) else end
        if "T" in end_str:
            end_str = end_str.split("T")[0]

        chunks = build_date_chunks(start_str, end_str)
        employees = self._client.employees.list()

        all_entries: list[ClockEntry] = []
        for emp in employees:
            for chunk_start, chunk_end in chunks:
                entries = self._client.employees.get_clock_entries(
                    emp.employee_id,
                    start_date=chunk_start,
                    end_date=chunk_end,
                )
                all_entries.extend(entries)

        # --- Filter by site_code locally ---
        site_code = self._client.site_code
        if site_code is not None:
            return [e for e in all_entries if e.site_code == site_code]
        return all_entries

    def _genuine_plan_sale_ids(
        self,
        v2_transactions: list[TransactionV2ListItem],
    ) -> set[str]:
        """Identify genuine new membership sales from v2 plan sale candidates.

        The v2 ``is_recurring_plan_sale`` flag includes both genuine new
        membership sales and plan upgrades/switches (e.g. Express → Clean).
        This method calls :meth:`~sonnys_data_client.resources.Transactions.get`
        on each candidate to check the v1 ``is_recurring_sale`` flag, which
        is ``True`` only for genuine new sales.

        Args:
            v2_transactions: The full v2 transaction list for the date range.

        Returns:
            A set of ``trans_id`` values for genuine new membership sales
            (excluding plan upgrades/switches).
        """
        genuine_ids: set[str] = set()
        for txn in v2_transactions:
            if not txn.is_recurring_plan_sale:
                continue
            detail = self._client.transactions.get(txn.trans_id)
            if getattr(detail, "is_recurring_sale", False):
                genuine_ids.add(txn.trans_id)
        return genuine_ids

    def retail_wash_count(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> int:
        """Count retail wash transactions for a date range.

        A retail wash is a ``type=wash`` transaction (v1) that is neither
        a recurring plan sale nor a recurring redemption (v2 flags).

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            The number of retail wash transactions in the date range.

        Raises:
            ValueError: If *start* is after *end*, or if a string cannot
                be parsed as a valid ISO-8601 date/datetime.

        Example::

            count = client.stats.retail_wash_count("2026-01-01", "2026-01-31")
            print(f"Retail washes: {count}")
        """
        wash_ids = {
            t.trans_id
            for t in self._fetch_transactions_by_type(start, end, "wash")
        }
        return sum(
            1 for t in self._fetch_transactions_v2(start, end)
            if t.trans_id in wash_ids
            and not t.is_recurring_plan_sale
            and not t.is_recurring_plan_redemption
        )

    def new_memberships_sold(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> int:
        """Count new membership sales for a date range.

        Fetches enriched v2 transactions and identifies those flagged as
        ``is_recurring_plan_sale``, then verifies each via the v1 detail
        endpoint to exclude plan upgrades/switches.  Only transactions
        where the v1 ``is_recurring_sale`` flag is ``True`` are counted.

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            The number of genuine new membership sales in the date range.

        Raises:
            ValueError: If *start* is after *end*, or if a string cannot
                be parsed as a valid ISO-8601 date/datetime.

        Example::

            count = client.stats.new_memberships_sold("2026-01-01", "2026-01-31")
            print(f"New memberships sold: {count}")
        """
        transactions = self._fetch_transactions_v2(start, end)
        return len(self._genuine_plan_sale_ids(transactions))

    def total_sales(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> SalesResult:
        """Compute revenue breakdown for a date range.

        Fetches all transactions via the enriched v2 endpoint and
        categorizes them into three buckets: recurring plan sales,
        recurring redemptions, and retail.  Returns a
        :class:`~sonnys_data_client.types.SalesResult` with grand totals
        and per-bucket revenue and count.

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            A :class:`~sonnys_data_client.types.SalesResult` containing
            the grand total, transaction count, and per-category
            breakdowns.

        Raises:
            ValueError: If *start* is after *end*, or if a string cannot
                be parsed as a valid ISO-8601 date/datetime.

        Example::

            result = client.stats.total_sales("2026-01-01", "2026-01-31")
            print(f"Total: ${result.total:.2f}")
            print(f"Memberships: ${result.recurring_plan_sales:.2f}")
        """
        transactions = self._fetch_transactions_v2(start, end)

        recurring_plan_sales = 0.0
        recurring_plan_sales_count = 0
        recurring_redemptions = 0.0
        recurring_redemptions_count = 0
        retail = 0.0
        retail_count = 0

        for txn in transactions:
            if txn.is_recurring_plan_sale:
                recurring_plan_sales += txn.total
                recurring_plan_sales_count += 1
            elif txn.is_recurring_plan_redemption:
                recurring_redemptions += txn.total
                recurring_redemptions_count += 1
            else:
                retail += txn.total
                retail_count += 1

        total = recurring_plan_sales + recurring_redemptions + retail
        count = recurring_plan_sales_count + recurring_redemptions_count + retail_count

        return SalesResult(
            total=total,
            count=count,
            recurring_plan_sales=recurring_plan_sales,
            recurring_plan_sales_count=recurring_plan_sales_count,
            recurring_redemptions=recurring_redemptions,
            recurring_redemptions_count=recurring_redemptions_count,
            retail=retail,
            retail_count=retail_count,
        )

    def total_washes(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> WashResult:
        """Compute wash volume breakdown for a date range.

        Fetches v2 transactions (for membership flags), v1 ``type=wash``
        (to identify car washes), and v1 ``type=recurring`` (to identify
        recharges).  Classification priority: redemption > plan sale >
        wash > recharge > unknown.

        ``eligible_wash_count`` is derived as
        ``total - member_wash_count - free_wash_count``.

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            A :class:`~sonnys_data_client.types.WashResult` containing the
            total wash count and per-category breakdowns.

        Raises:
            ValueError: If *start* is after *end*, or if a string cannot
                be parsed as a valid ISO-8601 date/datetime.

        Example::

            result = client.stats.total_washes("2026-01-01", "2026-01-31")
            print(f"Total washes: {result.total}")
            print(f"Retail: {result.retail_wash_count}")
            print(f"Member: {result.member_wash_count}")
            print(f"Eligible: {result.eligible_wash_count}")
            print(f"Free: {result.free_wash_count}")
        """
        wash_ids = {
            t.trans_id
            for t in self._fetch_transactions_by_type(start, end, "wash")
        }
        recurring_ids = {
            t.trans_id
            for t in self._fetch_transactions_by_type(start, end, "recurring")
        }
        v2_transactions = self._fetch_transactions_v2(start, end)

        member_wash_count = 0
        retail_wash_count = 0
        free_wash_count = 0
        plan_sale_wash_count = 0

        for txn in v2_transactions:
            if txn.is_recurring_plan_redemption:
                member_wash_count += 1
            elif txn.is_recurring_plan_sale:
                if txn.trans_id in wash_ids:
                    plan_sale_wash_count += 1
            elif txn.trans_id in wash_ids:
                # Wash takes priority over recurring (some are both)
                retail_wash_count += 1
                if txn.total == 0:
                    free_wash_count += 1
            elif txn.trans_id in recurring_ids:
                pass  # recharges — not a car wash
            elif txn.total >= 0:
                # Unknown non-negative type — count as a wash
                retail_wash_count += 1
                if txn.total == 0:
                    free_wash_count += 1

        total = member_wash_count + retail_wash_count + plan_sale_wash_count
        eligible_wash_count = total - member_wash_count - free_wash_count

        return WashResult(
            total=total,
            retail_wash_count=retail_wash_count,
            member_wash_count=member_wash_count,
            eligible_wash_count=eligible_wash_count,
            free_wash_count=free_wash_count,
        )

    def conversion_rate(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> ConversionResult:
        """Compute the membership conversion rate for a date range.

        Measures how effectively a site converts eligible wash customers
        into membership sign-ups.  The rate is computed as
        ``new_memberships / eligible_washes``.

        Eligible washes are derived from the total wash count:
        ``total_washes - member_washes - free_washes``.  This includes
        retail washes with ``total > 0``, plan sale washes, and unknown
        non-negative transaction types.  When there are zero eligible
        washes the rate is ``0.0`` (division-by-zero safe).

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            A :class:`~sonnys_data_client.types.ConversionResult` containing
            the conversion rate and component counts.

        Raises:
            ValueError: If *start* is after *end*, or if a string cannot
                be parsed as a valid ISO-8601 date/datetime.

        Example::

            result = client.stats.conversion_rate("2026-01-01", "2026-01-31")
            print(f"Conversion rate: {result.rate:.1%}")
            print(f"Memberships: {result.new_memberships}")
            print(f"Eligible washes: {result.eligible_washes}")
        """
        washes = self.total_washes(start, end)
        v2_transactions = self._fetch_transactions_v2(start, end)
        genuine_ids = self._genuine_plan_sale_ids(v2_transactions)
        new_memberships = len(genuine_ids)
        eligible_washes = washes.eligible_wash_count

        rate = new_memberships / eligible_washes if eligible_washes > 0 else 0.0

        return ConversionResult(
            rate=rate,
            new_memberships=new_memberships,
            eligible_washes=eligible_washes,
        )

    def report(
        self,
        start: str | datetime,
        end: str | datetime,
    ) -> StatsReport:
        """Compute all KPIs for a date range in a single call.

        Fetches v2 transactions, v1 ``type=wash``, v1 ``type=recurring``,
        and verifies each plan sale candidate via ``get()`` to exclude
        plan upgrades/switches.  Makes **3 bulk API calls** plus
        **~N detail calls** (one per v2 plan sale candidate, typically
        ~15/day) and computes every KPI locally.

        Args:
            start: Range start as an ISO-8601 string (e.g. ``"2026-01-01"``)
                or :class:`~datetime.datetime`.
            end: Range end as an ISO-8601 string or
                :class:`~datetime.datetime`.

        Returns:
            A :class:`~sonnys_data_client.types.StatsReport` containing
            ``sales``, ``washes``, ``new_memberships``, ``conversion``,
            ``period_start``, and ``period_end``.

        Raises:
            ValueError: If *start* is after *end*, or if a string cannot
                be parsed as a valid ISO-8601 date/datetime.

        Example::

            rpt = client.stats.report("2026-01-01", "2026-01-31")
            print(f"Revenue: ${rpt.sales.total:.2f}")
            print(f"Washes: {rpt.washes.total}")
            print(f"New members: {rpt.new_memberships}")
            print(f"Conversion: {rpt.conversion.rate:.1%}")
        """
        # --- 1. Fetch data (3 bulk API calls + ~N get() calls) ---
        v2_transactions = self._fetch_transactions_v2(start, end)
        wash_ids = {
            t.trans_id
            for t in self._fetch_transactions_by_type(start, end, "wash")
        }
        recurring_ids = {
            t.trans_id
            for t in self._fetch_transactions_by_type(start, end, "recurring")
        }
        # Verify plan sales via v1 get() to exclude upgrades/switches
        genuine_sale_ids = self._genuine_plan_sale_ids(v2_transactions)

        # --- 2. Single-pass classification ---
        recurring_plan_sales = 0.0
        recurring_plan_sales_count = 0
        recurring_redemptions = 0.0
        recurring_redemptions_count = 0
        retail = 0.0
        retail_count = 0
        retail_wash_count = 0
        free_wash_count = 0
        plan_sale_wash_count = 0

        for txn in v2_transactions:
            if txn.is_recurring_plan_sale:
                recurring_plan_sales += txn.total
                recurring_plan_sales_count += 1
                if txn.trans_id in wash_ids:
                    plan_sale_wash_count += 1
            elif txn.is_recurring_plan_redemption:
                recurring_redemptions += txn.total
                recurring_redemptions_count += 1
            else:
                retail += txn.total
                retail_count += 1
                if txn.trans_id in wash_ids:
                    # Wash takes priority over recurring (some are both)
                    retail_wash_count += 1
                    if txn.total == 0:
                        free_wash_count += 1
                elif txn.trans_id in recurring_ids:
                    pass  # recharges — not a car wash
                elif txn.total >= 0:
                    # Unknown non-negative type — count as a wash
                    retail_wash_count += 1
                    if txn.total == 0:
                        free_wash_count += 1

        sales_total = recurring_plan_sales + recurring_redemptions + retail
        sales_count = (
            recurring_plan_sales_count + recurring_redemptions_count + retail_count
        )

        # --- 3. SalesResult ---
        sales = SalesResult(
            total=sales_total,
            count=sales_count,
            recurring_plan_sales=recurring_plan_sales,
            recurring_plan_sales_count=recurring_plan_sales_count,
            recurring_redemptions=recurring_redemptions,
            recurring_redemptions_count=recurring_redemptions_count,
            retail=retail,
            retail_count=retail_count,
        )

        # --- 4. WashResult ---
        member_wash_count = recurring_redemptions_count
        new_memberships = len(genuine_sale_ids)
        total_washes = member_wash_count + retail_wash_count + plan_sale_wash_count
        # Eligible = total minus member washes minus free washes
        eligible_wash_count = total_washes - member_wash_count - free_wash_count
        washes = WashResult(
            total=total_washes,
            retail_wash_count=retail_wash_count,
            member_wash_count=member_wash_count,
            eligible_wash_count=eligible_wash_count,
            free_wash_count=free_wash_count,
        )

        # --- 5. ConversionResult ---
        rate = (
            new_memberships / eligible_wash_count
            if eligible_wash_count > 0
            else 0.0
        )

        conversion = ConversionResult(
            rate=rate,
            new_memberships=new_memberships,
            eligible_washes=eligible_wash_count,
        )

        # --- 6. Resolve period dates from original inputs ---
        period_start = start if isinstance(start, str) else start.date().isoformat()
        period_end = end if isinstance(end, str) else end.date().isoformat()
        if "T" in period_start:
            period_start = period_start.split("T")[0]
        if "T" in period_end:
            period_end = period_end.split("T")[0]

        # --- 7. Return unified report ---
        return StatsReport(
            sales=sales,
            washes=washes,
            new_memberships=new_memberships,
            conversion=conversion,
            period_start=period_start,
            period_end=period_end,
        )
