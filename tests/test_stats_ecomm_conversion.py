"""Tests for the ``exclude_ecomm`` flag on conversion-related stats.

E-Comm (online) terminals across every site carry the ``"E-Comm"`` marker
in their ``salesDeviceName``.  When ``exclude_ecomm=True`` is passed to
``new_memberships_sold()``, ``conversion_rate()``, or ``report()``, online
membership sign-ups are dropped from the numerator (new memberships).  The
denominator (eligible washes) is intentionally unaffected, since E-Comm
terminals do not perform in-lane car washes.

The device name is read from the transaction *detail* record that
``_genuine_plan_sale_ids`` already fetches to verify each sale, so the
exclusion adds no extra API calls.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from sonnys_data_client._client import SonnysClient
from sonnys_data_client.resources._stats import StatsResource, _is_ecomm_device
from sonnys_data_client.types._stats import WashResult
from sonnys_data_client.types._transactions import TransactionV2ListItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stats() -> StatsResource:
    client = SonnysClient("id", "key")
    client._rate_limiter.acquire = MagicMock(return_value=0.0)
    stats = StatsResource(client)
    # Bypass site-timezone lookup; tests stub the fetch helpers directly.
    stats._resolve_dates = MagicMock(return_value={"startDate": 0, "endDate": 1})
    return stats


def _v2_plan_sale(trans_id: str, total: float = 60.0) -> TransactionV2ListItem:
    return TransactionV2ListItem(
        trans_number=int(trans_id.split(":")[0]),
        trans_id=trans_id,
        total=total,
        date="2026-01-15",
        customer_id=None,
        is_recurring_plan_sale=True,
        is_recurring_plan_redemption=False,
        transaction_status="Completed",
    )


def _detail(*, is_recurring_sale: bool, device: str | None) -> SimpleNamespace:
    """Minimal stand-in for the v1 Transaction detail record.

    ``_genuine_plan_sale_ids`` only reads ``is_recurring_sale`` and
    ``sales_device_name`` off the detail, so a namespace is sufficient.
    """
    return SimpleNamespace(
        is_recurring_sale=is_recurring_sale,
        sales_device_name=device,
    )


def _wire_details(stats: StatsResource, details: dict[str, SimpleNamespace]) -> None:
    """Make ``client.transactions.get(trans_id)`` return canned details."""
    stats._client.transactions = MagicMock()
    stats._client.transactions.get = MagicMock(side_effect=lambda tid: details[tid])


# ---------------------------------------------------------------------------
# Unit: device marker detection
# ---------------------------------------------------------------------------


class TestIsEcommDevice:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("E-Comm 1", True),
            ("MAIN E-Comm", True),
            ("e-comm", True),  # case-insensitive
            ("E-COMM Lane", True),
            ("POS-1", False),
            ("Lane 3", False),
            ("Ecomm", False),  # marker requires the hyphen
            ("", False),
            (None, False),
        ],
    )
    def test_marker_detection(self, name: str | None, expected: bool) -> None:
        assert _is_ecomm_device(name) is expected


# ---------------------------------------------------------------------------
# new_memberships_sold(exclude_ecomm=...)
# ---------------------------------------------------------------------------


class TestNewMembershipsExcludeEcomm:
    def test_excludes_ecomm_sales_from_count(self) -> None:
        stats = _make_stats()
        v2 = [_v2_plan_sale("100:1"), _v2_plan_sale("200:1"), _v2_plan_sale("300:1")]
        stats._fetch_transactions_v2 = MagicMock(return_value=v2)
        _wire_details(
            stats,
            {
                "100:1": _detail(is_recurring_sale=True, device="Lane 1"),
                "200:1": _detail(is_recurring_sale=True, device="E-Comm 1"),
                "300:1": _detail(is_recurring_sale=True, device="POS-2"),
            },
        )

        assert stats.new_memberships_sold("2026-01-01", "2026-01-31") == 3
        assert (
            stats.new_memberships_sold(
                "2026-01-01", "2026-01-31", exclude_ecomm=True
            )
            == 2
        )

    def test_default_keeps_ecomm_sales(self) -> None:
        stats = _make_stats()
        v2 = [_v2_plan_sale("100:1"), _v2_plan_sale("200:1")]
        stats._fetch_transactions_v2 = MagicMock(return_value=v2)
        _wire_details(
            stats,
            {
                "100:1": _detail(is_recurring_sale=True, device="E-Comm 1"),
                "200:1": _detail(is_recurring_sale=True, device="E-Comm 2"),
            },
        )

        # Default (flag off) counts the online sign-ups.
        assert stats.new_memberships_sold("2026-01-01", "2026-01-31") == 2

    def test_upgrade_still_excluded_alongside_ecomm(self) -> None:
        # An upgrade (is_recurring_sale=False) is dropped regardless; the
        # E-Comm flag drops genuine online sales on top of that.
        stats = _make_stats()
        v2 = [_v2_plan_sale("100:1"), _v2_plan_sale("200:1"), _v2_plan_sale("300:1")]
        stats._fetch_transactions_v2 = MagicMock(return_value=v2)
        _wire_details(
            stats,
            {
                "100:1": _detail(is_recurring_sale=True, device="Lane 1"),
                "200:1": _detail(is_recurring_sale=False, device="Lane 2"),  # upgrade
                "300:1": _detail(is_recurring_sale=True, device="E-Comm 9"),
            },
        )

        assert stats.new_memberships_sold("2026-01-01", "2026-01-31") == 2
        assert (
            stats.new_memberships_sold(
                "2026-01-01", "2026-01-31", exclude_ecomm=True
            )
            == 1
        )


# ---------------------------------------------------------------------------
# conversion_rate(exclude_ecomm=...)
# ---------------------------------------------------------------------------


class TestConversionRateExcludeEcomm:
    def _wash_result(self, eligible: int) -> WashResult:
        return WashResult(
            total=eligible,
            retail_wash_count=eligible,
            member_wash_count=0,
            eligible_wash_count=eligible,
            free_wash_count=0,
        )

    def test_numerator_shrinks_denominator_unchanged(self) -> None:
        stats = _make_stats()
        stats.total_washes = MagicMock(return_value=self._wash_result(100))
        v2 = [_v2_plan_sale("100:1"), _v2_plan_sale("200:1")]
        stats._fetch_transactions_v2 = MagicMock(return_value=v2)
        _wire_details(
            stats,
            {
                "100:1": _detail(is_recurring_sale=True, device="Lane 1"),
                "200:1": _detail(is_recurring_sale=True, device="E-Comm 1"),
            },
        )

        full = stats.conversion_rate("2026-01-01", "2026-01-31")
        assert full.new_memberships == 2
        assert full.eligible_washes == 100
        assert full.rate == pytest.approx(0.02)

        in_lane = stats.conversion_rate(
            "2026-01-01", "2026-01-31", exclude_ecomm=True
        )
        assert in_lane.new_memberships == 1
        # Denominator is unchanged — E-Comm does not affect eligible washes.
        assert in_lane.eligible_washes == 100
        assert in_lane.rate == pytest.approx(0.01)

    def test_zero_eligible_is_division_safe(self) -> None:
        stats = _make_stats()
        stats.total_washes = MagicMock(return_value=self._wash_result(0))
        stats._fetch_transactions_v2 = MagicMock(return_value=[_v2_plan_sale("100:1")])
        _wire_details(
            stats, {"100:1": _detail(is_recurring_sale=True, device="E-Comm 1")}
        )

        result = stats.conversion_rate(
            "2026-01-01", "2026-01-31", exclude_ecomm=True
        )
        assert result.new_memberships == 0
        assert result.rate == 0.0


# ---------------------------------------------------------------------------
# report(exclude_ecomm=...)
# ---------------------------------------------------------------------------


class TestReportExcludeEcomm:
    def test_report_excludes_ecomm_from_memberships_and_conversion(self) -> None:
        stats = _make_stats()

        v2 = [_v2_plan_sale("100:1"), _v2_plan_sale("200:1")]
        stats._fetch_transactions_v2 = MagicMock(return_value=v2)
        # No washes from the type=wash endpoint; eligible washes come from
        # plan-sale washes only here. Keep it simple: 0 wash_ids overlap.
        stats._fetch_transactions_by_type = MagicMock(return_value=[])
        stats._fetch_all_clock_entries = MagicMock(return_value=[])
        _wire_details(
            stats,
            {
                "100:1": _detail(is_recurring_sale=True, device="Lane 1"),
                "200:1": _detail(is_recurring_sale=True, device="E-Comm 1"),
            },
        )

        full = stats.report("2026-01-01", "2026-01-31")
        assert full.new_memberships == 2
        assert full.conversion.new_memberships == 2

        excluded = stats.report("2026-01-01", "2026-01-31", exclude_ecomm=True)
        assert excluded.new_memberships == 1
        assert excluded.conversion.new_memberships == 1
        # Sales breakdown counts the plan sale revenue regardless of the flag.
        assert excluded.sales.recurring_plan_sales_count == 2
