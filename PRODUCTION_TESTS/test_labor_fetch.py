"""Smoke test for _fetch_all_clock_entries on JOLIET (5-day range)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sonnys_data_client import SonnysClient

API_ID = os.environ.get("X_SONNYS_API_ID", "washu")
API_KEY = os.environ.get("X_SONNYS_API_KEY", "6663105e0887dffd4ee7aa72cb416")
SITE = "JOLIET"

START = "2026-01-27"
END = "2026-01-31"

print(f"{'':=<80}")
print(f"  LABOR FETCH SMOKE TEST")
print(f"  Site: {SITE}  |  Range: {START} to {END}")
print(f"{'':=<80}")
print()

with SonnysClient(api_id=API_ID, api_key=API_KEY, site_code=SITE) as client:
    # Get employee count
    employees = client.employees.list()
    print(f"Employees fetched:     {len(employees)}")

    # Fetch clock entries
    entries = client.stats._fetch_all_clock_entries(START, END)
    print(f"Clock entries returned: {len(entries)}")
    print()

    # Hours summary
    total_regular = sum(e.regular_hours for e in entries)
    total_overtime = sum(e.overtime_hours for e in entries)
    print(f"Total regular hours:   {total_regular:.2f}")
    print(f"Total overtime hours:  {total_overtime:.2f}")
    print()

    # Unique site codes
    site_codes = sorted({e.site_code for e in entries})
    print(f"Unique site codes:     {site_codes}")
    print()

    # Sample entry
    if entries:
        e = entries[0]
        print("Sample entry (first):")
        print(f"  clock_in:               {e.clock_in}")
        print(f"  clock_out:              {e.clock_out}")
        print(f"  regular_rate:           {e.regular_rate}")
        print(f"  regular_hours:          {e.regular_hours}")
        print(f"  overtime_eligible:      {e.overtime_eligible}")
        print(f"  overtime_rate:          {e.overtime_rate}")
        print(f"  overtime_hours:         {e.overtime_hours}")
        print(f"  was_modified:           {e.was_modified}")
        print(f"  modification_timestamp: {e.modification_timestamp}")
        print(f"  was_created_in_back_office: {e.was_created_in_back_office}")
        print(f"  site_code:              {e.site_code}")
    print()

    # Assertion
    assert len(entries) >= 1, "Expected at least 1 clock entry for active site"
    print("PASS: At least 1 clock entry returned.")
