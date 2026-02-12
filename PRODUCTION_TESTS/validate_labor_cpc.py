"""Validate labor CPC methods against real API data.

Set environment variables before running:
    SONNYS_API_ID       Your Sonny's API ID
    SONNYS_API_KEY      Your Sonny's API key
    SONNYS_SITE_CODE    Site code to validate (e.g. JOLIET)

Usage:
    python scripts/validate_labor_cpc.py
"""

import os
import sys
import time
from datetime import datetime, timedelta

from sonnys_data_client import SonnysClient


def get_last_full_week() -> tuple[str, str]:
    """Return (start, end) ISO date strings for the most recent full Mon-Sun week."""
    today = datetime.now().date()
    # Go back to most recent Sunday
    days_since_sunday = (today.weekday() + 1) % 7
    last_sunday = today - timedelta(days=max(days_since_sunday, 1))
    last_monday = last_sunday - timedelta(days=6)
    return last_monday.isoformat(), last_sunday.isoformat()


def fmt_dollars(value: float) -> str:
    return f"${value:,.2f}"


def fmt_hours(value: float) -> str:
    return f"{value:,.1f}h"


def main() -> None:
    api_id = os.environ.get("SONNYS_API_ID")
    api_key = os.environ.get("SONNYS_API_KEY")
    site_code = os.environ.get("SONNYS_SITE_CODE")

    missing = []
    if not api_id:
        missing.append("SONNYS_API_ID")
    if not api_key:
        missing.append("SONNYS_API_KEY")
    if not site_code:
        missing.append("SONNYS_SITE_CODE")

    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print()
        print("Set them before running:")
        print("  export SONNYS_API_ID=your-api-id")
        print("  export SONNYS_API_KEY=your-api-key")
        print("  export SONNYS_SITE_CODE=JOLIET")
        sys.exit(1)

    start, end = get_last_full_week()

    print("=" * 60)
    print("  LABOR CPC VALIDATION")
    print("=" * 60)
    print(f"  Site:        {site_code}")
    print(f"  Date range:  {start} to {end}")
    print("=" * 60)
    print()

    timings: dict[str, float] = {}

    with SonnysClient(api_id=api_id, api_key=api_key, site_code=site_code) as client:

        # --- 1. total_labor_cost() ---
        print("-" * 60)
        print("  1. total_labor_cost()")
        print("-" * 60)
        t0 = time.perf_counter()
        labor = client.stats.total_labor_cost(start, end)
        timings["total_labor_cost"] = time.perf_counter() - t0

        print(f"  Total cost:      {fmt_dollars(labor.total_cost)}")
        print(f"  Regular cost:    {fmt_dollars(labor.regular_cost)}  ({fmt_hours(labor.regular_hours)})")
        print(f"  Overtime cost:   {fmt_dollars(labor.overtime_cost)}  ({fmt_hours(labor.overtime_hours)})")
        print(f"  Total hours:     {fmt_hours(labor.total_hours)}")
        print(f"  Clock entries:   {labor.entry_count}")
        print()

        # --- 2. cost_per_car() ---
        print("-" * 60)
        print("  2. cost_per_car()")
        print("-" * 60)
        t0 = time.perf_counter()
        cpc = client.stats.cost_per_car(start, end)
        timings["cost_per_car"] = time.perf_counter() - t0

        print(f"  Cost per car:    {fmt_dollars(cpc.cost_per_car)}")
        print(f"  Total labor:     {fmt_dollars(cpc.total_labor_cost)}")
        print(f"  Total washes:    {cpc.total_washes}")
        print()

        # --- 3. report() ---
        print("-" * 60)
        print("  3. report()")
        print("-" * 60)
        t0 = time.perf_counter()
        rpt = client.stats.report(start, end)
        timings["report"] = time.perf_counter() - t0

        print(f"  Period:          {rpt.period_start} to {rpt.period_end}")
        print()
        print(f"  Sales total:     {fmt_dollars(rpt.sales.total)}  ({rpt.sales.count} transactions)")
        print(f"    Plan sales:    {fmt_dollars(rpt.sales.recurring_plan_sales)}  ({rpt.sales.recurring_plan_sales_count})")
        print(f"    Redemptions:   {fmt_dollars(rpt.sales.recurring_redemptions)}  ({rpt.sales.recurring_redemptions_count})")
        print(f"    Retail:        {fmt_dollars(rpt.sales.retail)}  ({rpt.sales.retail_count})")
        print()
        print(f"  Total washes:    {rpt.washes.total}")
        print(f"    Retail:        {rpt.washes.retail_wash_count}")
        print(f"    Member:        {rpt.washes.member_wash_count}")
        print(f"    Eligible:      {rpt.washes.eligible_wash_count}")
        print(f"    Free:          {rpt.washes.free_wash_count}")
        print()
        print(f"  New memberships: {rpt.new_memberships}")
        print(f"  Conversion rate: {rpt.conversion.rate:.1%}")
        print()
        print(f"  Labor cost:      {fmt_dollars(rpt.labor.total_cost)}  ({rpt.labor.entry_count} entries)")
        print(f"    Regular:       {fmt_dollars(rpt.labor.regular_cost)}  ({fmt_hours(rpt.labor.regular_hours)})")
        print(f"    Overtime:      {fmt_dollars(rpt.labor.overtime_cost)}  ({fmt_hours(rpt.labor.overtime_hours)})")
        print()
        print(f"  Cost per car:    {fmt_dollars(rpt.cost_per_car.cost_per_car)}")
        print()

    # --- Timing summary ---
    print("=" * 60)
    print("  TIMING SUMMARY")
    print("=" * 60)
    total_time = sum(timings.values())
    for method, elapsed in timings.items():
        print(f"  {method + ':' :<25} {elapsed:>6.1f}s")
    print(f"  {'total:' :<25} {total_time:>6.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
