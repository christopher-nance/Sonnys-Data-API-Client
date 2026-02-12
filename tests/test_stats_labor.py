"""Tests for labor data fetching and cost aggregation in StatsResource."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from sonnys_data_client._client import SonnysClient
from sonnys_data_client.resources._stats import StatsResource
from sonnys_data_client.types._employees import ClockEntry, EmployeeListItem
from sonnys_data_client.types._stats import LaborCostResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client() -> SonnysClient:
    """Create a SonnysClient with mocked internals for resource testing."""
    client = SonnysClient("id", "key")
    client._rate_limiter.acquire = MagicMock(return_value=0.0)
    return client


def _make_clock_entry(**overrides: object) -> ClockEntry:
    """Build a ClockEntry with sensible defaults and optional overrides."""
    defaults = {
        "clock_in": "2026-01-15T08:00:00",
        "clock_out": "2026-01-15T16:00:00",
        "regular_rate": 15.0,
        "regular_hours": 8.0,
        "overtime_eligible": True,
        "overtime_rate": 22.5,
        "overtime_hours": 0.0,
        "was_modified": False,
        "modification_timestamp": None,
        "was_created_in_back_office": False,
        "site_code": "MAIN",
    }
    defaults.update(overrides)
    return ClockEntry(**defaults)


def _make_employee(employee_id: int, first_name: str = "Test", last_name: str = "User") -> EmployeeListItem:
    """Build an EmployeeListItem with the given ID."""
    return EmployeeListItem(
        first_name=first_name,
        last_name=last_name,
        employee_id=employee_id,
    )


# ---------------------------------------------------------------------------
# Tests for _fetch_all_clock_entries()
# ---------------------------------------------------------------------------


class TestFetchAllClockEntries:
    """Tests for StatsResource._fetch_all_clock_entries()."""

    def test_two_employees_one_chunk_each(self) -> None:
        """Two employees with 5-day range (within 14-day limit), each returns 2 entries."""
        client = _make_client()
        stats = StatsResource(client)

        emp1 = _make_employee(101, "Alice", "Smith")
        emp2 = _make_employee(102, "Bob", "Jones")
        client.employees = MagicMock()
        client.employees.list = MagicMock(return_value=[emp1, emp2])

        entry_a1 = _make_clock_entry(site_code="MAIN", clock_in="2026-01-01T08:00:00")
        entry_a2 = _make_clock_entry(site_code="MAIN", clock_in="2026-01-02T08:00:00")
        entry_b1 = _make_clock_entry(site_code="MAIN", clock_in="2026-01-03T08:00:00")
        entry_b2 = _make_clock_entry(site_code="MAIN", clock_in="2026-01-04T08:00:00")

        client.employees.get_clock_entries = MagicMock(
            side_effect=[[entry_a1, entry_a2], [entry_b1, entry_b2]]
        )
        client.site_code = None

        result = stats._fetch_all_clock_entries("2026-01-01", "2026-01-05")

        assert len(result) == 4
        client.employees.list.assert_called_once()
        assert client.employees.get_clock_entries.call_count == 2

        client.close()

    def test_date_range_requiring_chunking(self) -> None:
        """1 employee with 20-day range splits into 14+6 day chunks."""
        client = _make_client()
        stats = StatsResource(client)

        emp = _make_employee(201)
        client.employees = MagicMock()
        client.employees.list = MagicMock(return_value=[emp])

        chunk1_entries = [_make_clock_entry(clock_in="2026-01-01T08:00:00")]
        chunk2_entries = [_make_clock_entry(clock_in="2026-01-16T08:00:00")]

        client.employees.get_clock_entries = MagicMock(
            side_effect=[chunk1_entries, chunk2_entries]
        )
        client.site_code = None

        result = stats._fetch_all_clock_entries("2026-01-01", "2026-01-20")

        assert len(result) == 2
        assert client.employees.get_clock_entries.call_count == 2

        # Verify the chunk date ranges passed to get_clock_entries
        call_args_list = client.employees.get_clock_entries.call_args_list
        # First chunk: 2026-01-01 to 2026-01-14
        assert call_args_list[0][0] == (201,)
        assert call_args_list[0][1] == {"start_date": "2026-01-01", "end_date": "2026-01-14"}
        # Second chunk: 2026-01-15 to 2026-01-20
        assert call_args_list[1][0] == (201,)
        assert call_args_list[1][1] == {"start_date": "2026-01-15", "end_date": "2026-01-20"}

        client.close()

    def test_site_code_filtering(self) -> None:
        """Only entries matching client.site_code are returned."""
        client = _make_client()
        stats = StatsResource(client)

        emp = _make_employee(301)
        client.employees = MagicMock()
        client.employees.list = MagicMock(return_value=[emp])

        joliet_entry = _make_clock_entry(site_code="JOLIET")
        other_entry = _make_clock_entry(site_code="OTHER")
        joliet_entry2 = _make_clock_entry(site_code="JOLIET")

        client.employees.get_clock_entries = MagicMock(
            return_value=[joliet_entry, other_entry, joliet_entry2]
        )
        client.site_code = "JOLIET"

        result = stats._fetch_all_clock_entries("2026-01-01", "2026-01-05")

        assert len(result) == 2
        assert all(e.site_code == "JOLIET" for e in result)

        client.close()

    def test_no_site_code_returns_all(self) -> None:
        """When client.site_code is None, all entries are returned unfiltered."""
        client = _make_client()
        stats = StatsResource(client)

        emp = _make_employee(401)
        client.employees = MagicMock()
        client.employees.list = MagicMock(return_value=[emp])

        entry_main = _make_clock_entry(site_code="MAIN")
        entry_joliet = _make_clock_entry(site_code="JOLIET")
        entry_other = _make_clock_entry(site_code="OTHER")

        client.employees.get_clock_entries = MagicMock(
            return_value=[entry_main, entry_joliet, entry_other]
        )
        client.site_code = None

        result = stats._fetch_all_clock_entries("2026-01-01", "2026-01-05")

        assert len(result) == 3

        client.close()

    def test_empty_employee_list(self) -> None:
        """Empty employee list returns empty results, get_clock_entries never called."""
        client = _make_client()
        stats = StatsResource(client)

        client.employees = MagicMock()
        client.employees.list = MagicMock(return_value=[])
        client.employees.get_clock_entries = MagicMock()
        client.site_code = None

        result = stats._fetch_all_clock_entries("2026-01-01", "2026-01-05")

        assert result == []
        client.employees.get_clock_entries.assert_not_called()

        client.close()

    def test_datetime_input_normalization(self) -> None:
        """datetime objects are normalized to YYYY-MM-DD strings via .isoformat()[:10]."""
        client = _make_client()
        stats = StatsResource(client)

        emp = _make_employee(601)
        client.employees = MagicMock()
        client.employees.list = MagicMock(return_value=[emp])

        entry = _make_clock_entry()
        client.employees.get_clock_entries = MagicMock(return_value=[entry])
        client.site_code = None

        start_dt = datetime(2026, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        end_dt = datetime(2026, 1, 5, 18, 45, 0, tzinfo=timezone.utc)

        result = stats._fetch_all_clock_entries(start_dt, end_dt)

        assert len(result) == 1

        # Verify the date strings passed to get_clock_entries are YYYY-MM-DD
        call_kwargs = client.employees.get_clock_entries.call_args[1]
        assert call_kwargs["start_date"] == "2026-01-01"
        assert call_kwargs["end_date"] == "2026-01-05"

        client.close()


# ---------------------------------------------------------------------------
# Tests for total_labor_cost()
# ---------------------------------------------------------------------------


class TestTotalLaborCost:
    """Tests for StatsResource.total_labor_cost()."""

    def test_normal_mix_regular_and_overtime(self) -> None:
        """3 entries with mixed regular and overtime compute correct totals."""
        client = _make_client()
        stats = StatsResource(client)

        entries = [
            # 8h regular @ $15/hr = $120, 0h OT
            _make_clock_entry(regular_rate=15.0, regular_hours=8.0, overtime_rate=0.0, overtime_hours=0.0),
            # 8h regular @ $12/hr = $96, 2h OT @ $18/hr = $36
            _make_clock_entry(regular_rate=12.0, regular_hours=8.0, overtime_rate=18.0, overtime_hours=2.0),
            # 6h regular @ $20/hr = $120, 0h OT
            _make_clock_entry(regular_rate=20.0, regular_hours=6.0, overtime_rate=0.0, overtime_hours=0.0),
        ]

        with patch.object(StatsResource, "_fetch_all_clock_entries", return_value=entries):
            result = stats.total_labor_cost("2026-01-01", "2026-01-31")

        assert isinstance(result, LaborCostResult)
        assert result.regular_cost == 336.0  # 120 + 96 + 120
        assert result.overtime_cost == 36.0  # 0 + 36 + 0
        assert result.total_cost == 372.0  # 336 + 36
        assert result.regular_hours == 22.0  # 8 + 8 + 6
        assert result.overtime_hours == 2.0  # 0 + 2 + 0
        assert result.total_hours == 24.0  # 22 + 2
        assert result.entry_count == 3

        client.close()

    def test_empty_entries(self) -> None:
        """No clock entries returns all zeros."""
        client = _make_client()
        stats = StatsResource(client)

        with patch.object(StatsResource, "_fetch_all_clock_entries", return_value=[]):
            result = stats.total_labor_cost("2026-01-01", "2026-01-31")

        assert result.total_cost == 0.0
        assert result.regular_cost == 0.0
        assert result.overtime_cost == 0.0
        assert result.regular_hours == 0.0
        assert result.overtime_hours == 0.0
        assert result.total_hours == 0.0
        assert result.entry_count == 0

        client.close()

    def test_only_regular_hours(self) -> None:
        """Entries with only regular hours have zero overtime cost."""
        client = _make_client()
        stats = StatsResource(client)

        entries = [
            _make_clock_entry(regular_rate=15.0, regular_hours=8.0, overtime_rate=0.0, overtime_hours=0.0),
            _make_clock_entry(regular_rate=18.0, regular_hours=6.0, overtime_rate=0.0, overtime_hours=0.0),
        ]

        with patch.object(StatsResource, "_fetch_all_clock_entries", return_value=entries):
            result = stats.total_labor_cost("2026-01-01", "2026-01-31")

        assert result.overtime_cost == 0.0
        assert result.overtime_hours == 0.0
        assert result.regular_cost == 228.0  # (15*8) + (18*6) = 120 + 108
        assert result.total_cost == result.regular_cost

        client.close()

    def test_only_overtime_hours(self) -> None:
        """Entry with only overtime hours has zero regular cost."""
        client = _make_client()
        stats = StatsResource(client)

        entries = [
            _make_clock_entry(regular_rate=0.0, regular_hours=0.0, overtime_rate=25.0, overtime_hours=4.0),
        ]

        with patch.object(StatsResource, "_fetch_all_clock_entries", return_value=entries):
            result = stats.total_labor_cost("2026-01-01", "2026-01-31")

        assert result.regular_cost == 0.0
        assert result.overtime_cost == 100.0  # 25 * 4
        assert result.total_cost == 100.0

        client.close()

    def test_single_entry_precision(self) -> None:
        """Exact float multiplication with no rounding."""
        client = _make_client()
        stats = StatsResource(client)

        entries = [
            _make_clock_entry(regular_rate=15.75, regular_hours=7.5, overtime_rate=0.0, overtime_hours=0.0),
        ]

        with patch.object(StatsResource, "_fetch_all_clock_entries", return_value=entries):
            result = stats.total_labor_cost("2026-01-01", "2026-01-31")

        assert result.regular_cost == 118.125  # 15.75 * 7.5
        assert result.total_cost == 118.125
        assert result.entry_count == 1

        client.close()
