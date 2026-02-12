# Stats

The **Stats** resource provides computed business analytics and KPIs derived
from transaction data. Unlike other resources that wrap REST endpoints
directly, `client.stats` fetches raw data from the API and aggregates it
locally, giving you ready-to-use metrics like total sales, wash volume, new
memberships, and conversion rates without writing any aggregation logic
yourself.

!!! note "Rinsed alignment"
    Stats calculations are designed to align with
    **[Rinsed: The Car Wash CRM](https://www.rinsed.co/)** and its
    reporting metrics as closely as possible.  Rinsed is the system of record
    for WashU membership and conversion reporting, so matching its numbers is
    the primary accuracy benchmark for this library.

    Wash classification uses a combination of v2 transaction flags
    (`is_recurring_plan_sale`, `is_recurring_plan_redemption`) and v1 type
    endpoints (`type=wash`, `type=recurring`) to accurately distinguish car
    washes from recharges and refunds.  Membership counts are verified via v1
    detail lookups to exclude plan upgrades/switches.

    In validation testing across 31 days of JOLIET data (January 2026),
    compared against the Rinsed *Daily Conversion Detail* report:

    | Metric | Exact-match days | Monthly gap | Accuracy |
    |--------|:----------------:|:-----------:|:--------:|
    | **Member washes** | 31/31 (100%) | 0 of 8,506 | 100% |
    | **Free washes** | 31/31 (100%) | 0 of 319 | 100% |
    | **New memberships** | 31/31 (100%) | 0 of 438 | 100% |
    | **Total washes** | 22/31 (71%) | +11 of 12,097 | 99.91% |
    | **Eligible washes** | 22/31 (71%) | +11 of 3,272 | 99.66% |
    | **Perfect match (all 5)** | **22/31 (71%)** | | |

    The +11 total-wash gap (spread across 9 days, each off by 1–2 washes)
    likely reflects transaction-boundary timing differences between the
    Sonny's API and Rinsed's data pipeline.  Eligible washes inherit the same
    gap since `eligible = total − member − free`.

## Choosing the Right Method

The stats resource offers eight methods. Pick the one that matches your use case:

| Method | Returns | Description | API Calls |
|--------|---------|-------------|-----------|
| `total_sales(start, end)` | `SalesResult` | Revenue breakdown by category (recurring, retail) | 1 |
| `total_washes(start, end)` | `WashResult` | Wash volume breakdown (member, retail, eligible, free) | 3 |
| `retail_wash_count(start, end)` | `int` | Count of retail wash transactions | 2 |
| `new_memberships_sold(start, end)` | `int` | Count of genuine new membership sales | 1 + ~N |
| `conversion_rate(start, end)` | `ConversionResult` | Membership conversion rate KPI | 4 + ~N |
| `total_labor_cost(start, end)` | `LaborCostResult` | Labor cost breakdown (regular/overtime) from clock entries | N_emp x ceil(days/14) + 1 |
| `cost_per_car(start, end)` | `CostPerCarResult` | Labor cost per car washed | N_emp x ceil(days/14) + 4 |
| `report(start, end)` | `StatsReport` | All KPIs in a single call (most efficient) | 4 + N_emp x ceil(days/14) + ~N |

Where **~N** is the number of v2 plan sale candidates verified via `get()`
(typically ~15/day).  This verification excludes plan upgrades/switches from
membership counts to match Rinsed exactly.

Use individual methods when you need a single metric. Use `report()` when you
need multiple KPIs -- it shares bulk data fetches across KPIs and only
verifies plan sales once.

## Date Range Input

All stats methods accept a `start` and `end` parameter for the date range. You
can pass either an ISO-8601 date string or a Python `datetime` object:

```python
# ISO-8601 strings
result = client.stats.total_sales("2026-01-01", "2026-01-31")

# datetime objects
from datetime import datetime
result = client.stats.total_sales(
    datetime(2026, 1, 1),
    datetime(2026, 1, 31),
)
```

Date-only strings automatically get boundary times applied (`00:00:01` start,
`23:59:59` end) in the site's local timezone, then converted to UTC.  Naive
datetime objects are assumed to be UTC.  Timezone-aware datetimes are converted
to UTC.  If `start` is after `end`, a `ValueError` is raised.

## Methods

### `total_sales(start, end) -> SalesResult`

Compute a revenue breakdown for a date range. Fetches all transactions via the
enriched v2 endpoint and categorizes them into three buckets: recurring plan
sales, recurring redemptions, and retail.

```python
result = client.stats.total_sales("2026-01-01", "2026-01-31")

print(f"Total revenue: ${result.total:.2f} ({result.count} transactions)")
print(f"Recurring plan sales: ${result.recurring_plan_sales:.2f} ({result.recurring_plan_sales_count})")
print(f"Recurring redemptions: ${result.recurring_redemptions:.2f} ({result.recurring_redemptions_count})")
print(f"Retail: ${result.retail:.2f} ({result.retail_count})")
```

**`SalesResult` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `total` | `float` | Grand total revenue |
| `count` | `int` | Total transaction count |
| `recurring_plan_sales` | `float` | Revenue from recurring plan sales |
| `recurring_plan_sales_count` | `int` | Number of recurring plan sale transactions |
| `recurring_redemptions` | `float` | Revenue from recurring redemptions |
| `recurring_redemptions_count` | `int` | Number of recurring redemption transactions |
| `retail` | `float` | Revenue from retail transactions |
| `retail_count` | `int` | Number of retail transactions |

### `total_washes(start, end) -> WashResult`

Compute wash volume for a date range. Uses three data sources to classify
transactions accurately:

- **v2 endpoint** -- provides `is_recurring_plan_sale` and `is_recurring_plan_redemption` flags
- **v1 `type=wash`** -- identifies actual car wash transactions
- **v1 `type=recurring`** -- identifies recharges (monthly billing) to exclude

Classification priority: redemption > plan sale > wash > recharge > unknown.
Transactions in both `type=wash` and `type=recurring` are treated as washes.
Negative-total transactions (refunds) are excluded entirely.

```python
result = client.stats.total_washes("2026-01-01", "2026-01-31")

print(f"Total washes: {result.total}")
print(f"Member washes: {result.member_wash_count}")
print(f"Retail washes: {result.retail_wash_count}")
print(f"Eligible washes: {result.eligible_wash_count}")
print(f"Free washes: {result.free_wash_count}")
```

**`WashResult` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `total` | `int` | Total wash count (member + retail + plan sale washes) |
| `member_wash_count` | `int` | Membership redemption washes |
| `retail_wash_count` | `int` | Non-member washes (includes unknown non-negative types) |
| `eligible_wash_count` | `int` | Derived: `total - member - free`. Denominator for conversion rate |
| `free_wash_count` | `int` | Washes with `total == 0` (complimentary) |

### `retail_wash_count(start, end) -> int`

Count retail wash transactions for a date range. A retail wash is a `type=wash`
transaction that is neither a recurring plan sale nor a recurring redemption.

```python
count = client.stats.retail_wash_count("2026-01-01", "2026-01-31")
print(f"Retail washes: {count}")
```

### `new_memberships_sold(start, end) -> int`

Count genuine new membership sales for a date range. Fetches v2 transactions
to identify plan sale candidates, then verifies each via the v1 detail
endpoint (`is_recurring_sale`) to exclude plan upgrades/switches (e.g.
upgrading from Express to Clean). Only brand-new sign-ups and reactivations
are counted.

```python
count = client.stats.new_memberships_sold("2026-01-01", "2026-01-31")
print(f"New memberships sold: {count}")
```

### `conversion_rate(start, end) -> ConversionResult`

Compute the membership conversion rate for a date range. Measures how
effectively a site converts eligible wash customers into membership sign-ups.
The rate is computed as `new_memberships / eligible_washes`.

Eligible washes are derived from total washes: `total - member - free`. This
includes retail washes with `total > 0`, plan sale washes, and unknown
non-negative transaction types.

```python
result = client.stats.conversion_rate("2026-01-01", "2026-01-31")

print(f"Conversion rate: {result.rate:.1%}")
print(f"New memberships: {result.new_memberships}")
print(f"Eligible washes: {result.eligible_washes}")
```

When there are zero eligible washes the rate is `0.0` (division-by-zero safe).

**`ConversionResult` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `rate` | `float` | Conversion rate as a decimal (e.g. `0.15` = 15%) |
| `new_memberships` | `int` | Number of genuine new membership sales |
| `eligible_washes` | `int` | Eligible washes (denominator) |

### `total_labor_cost(start, end) -> LaborCostResult`

Compute labor cost breakdown for a date range. Fetches clock entries for all
employees via a 14-day windowed bulk fetch (the API's hard maximum per
request), then aggregates regular and overtime costs in a single pass. Each
entry's cost is computed as `rate * hours` for the corresponding pay type.
Site-code filtering is applied locally after fetching, because the
clock-entries endpoint does not support a site filter.

```python
result = client.stats.total_labor_cost("2026-01-01", "2026-01-31")

print(f"Total labor cost: ${result.total_cost:.2f}")
print(f"Regular: ${result.regular_cost:.2f} ({result.regular_hours:.1f}h)")
print(f"Overtime: ${result.overtime_cost:.2f} ({result.overtime_hours:.1f}h)")
print(f"Total hours: {result.total_hours:.1f}")
print(f"Clock entries: {result.entry_count}")
```

**`LaborCostResult` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `total_cost` | `float` | Combined regular and overtime cost |
| `regular_cost` | `float` | Sum of `regular_rate * regular_hours` across all entries |
| `overtime_cost` | `float` | Sum of `overtime_rate * overtime_hours` across all entries |
| `regular_hours` | `float` | Total regular hours worked |
| `overtime_hours` | `float` | Total overtime hours worked |
| `total_hours` | `float` | Combined hours (`regular_hours + overtime_hours`) |
| `entry_count` | `int` | Number of clock entries aggregated |

### `cost_per_car(start, end) -> CostPerCarResult`

Compute labor cost per car for a date range. Divides total labor cost by total
wash volume to measure labor efficiency. A value of `4.25` means the site spent
$4.25 in labor for each car washed. When there are zero washes the result is
`0.0` (division-by-zero safe).

```python
result = client.stats.cost_per_car("2026-01-01", "2026-01-31")

print(f"Cost per car: ${result.cost_per_car:.2f}")
print(f"Total labor cost: ${result.total_labor_cost:.2f}")
print(f"Total washes: {result.total_washes}")
```

**`CostPerCarResult` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `cost_per_car` | `float` | Total labor cost divided by total washes (`0.0` when no washes) |
| `total_labor_cost` | `float` | Aggregate labor cost from `LaborCostResult` |
| `total_washes` | `int` | Wash count from `WashResult` |

### `report(start, end) -> StatsReport`

Compute all KPIs for a date range in a single call, including sales, washes,
memberships, conversion rate, labor costs, and cost per car. Makes **4 bulk
API calls** (3 transaction + 1 employee list) plus **N_emp x ceil(days/14)
clock-entry calls** and **~N detail calls** (one per plan sale candidate,
typically ~15/day) to verify memberships. This is far more efficient than
calling each method individually, which would duplicate bulk fetches, clock
entry iterations, and detail lookups.

```python
rpt = client.stats.report("2026-01-01", "2026-01-31")

print(f"Period: {rpt.period_start} to {rpt.period_end}")
print(f"Revenue: ${rpt.sales.total:.2f} ({rpt.sales.count} transactions)")
print(f"Washes: {rpt.washes.total} (member: {rpt.washes.member_wash_count}, retail: {rpt.washes.retail_wash_count})")
print(f"Eligible: {rpt.washes.eligible_wash_count}, Free: {rpt.washes.free_wash_count}")
print(f"New memberships: {rpt.new_memberships}")
print(f"Conversion rate: {rpt.conversion.rate:.1%}")
print(f"Labor cost: ${rpt.labor.total_cost:.2f}")
print(f"Cost per car: ${rpt.cost_per_car.cost_per_car:.2f}")
```

**`StatsReport` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `sales` | `SalesResult` | Revenue breakdown (see `total_sales()` above) |
| `washes` | `WashResult` | Wash volume breakdown (see `total_washes()` above) |
| `new_memberships` | `int` | Count of recurring plan sales |
| `conversion` | `ConversionResult` | Conversion rate KPI (see `conversion_rate()` above) |
| `labor` | `LaborCostResult` | Labor cost breakdown (see `total_labor_cost()` above) |
| `cost_per_car` | `CostPerCarResult` | Labor cost per car KPI (see `cost_per_car()` above) |
| `period_start` | `str` | ISO-8601 date string for start of report range |
| `period_end` | `str` | ISO-8601 date string for end of report range |

## Examples

### Monthly performance snapshot

```python
from sonnys_data_client import SonnysClient

with SonnysClient(api_id="your-api-id", api_key="your-api-key",
                   site_code="JOLIET") as client:
    rpt = client.stats.report("2026-01-01", "2026-01-31")

    print(f"January 2026 Performance")
    print(f"{'='*40}")
    print(f"Revenue:       ${rpt.sales.total:>10,.2f}")
    print(f"  Memberships: ${rpt.sales.recurring_plan_sales:>10,.2f}")
    print(f"  Retail:      ${rpt.sales.retail:>10,.2f}")
    print(f"Washes:        {rpt.washes.total:>10,}")
    print(f"  Member:      {rpt.washes.member_wash_count:>10,}")
    print(f"  Eligible:    {rpt.washes.eligible_wash_count:>10,}")
    print(f"  Free:        {rpt.washes.free_wash_count:>10,}")
    print(f"New members:   {rpt.new_memberships:>10,}")
    print(f"Conversion:    {rpt.conversion.rate:>9.1%}")
    print(f"Labor:         ${rpt.labor.total_cost:>10,.2f}")
    print(f"  Regular:     ${rpt.labor.regular_cost:>10,.2f}")
    print(f"  Overtime:    ${rpt.labor.overtime_cost:>10,.2f}")
    print(f"Cost/car:      ${rpt.cost_per_car.cost_per_car:>10.2f}")
```

### Compare two periods

```python
from sonnys_data_client import SonnysClient

with SonnysClient(api_id="your-api-id", api_key="your-api-key",
                   site_code="JOLIET") as client:
    jan = client.stats.report("2026-01-01", "2026-01-31")
    feb = client.stats.report("2026-02-01", "2026-02-28")

    rev_change = feb.sales.total - jan.sales.total
    wash_change = feb.washes.total - jan.washes.total

    print(f"Revenue change: ${rev_change:+,.2f}")
    print(f"Wash volume change: {wash_change:+,}")
    print(f"Conversion: {jan.conversion.rate:.1%} -> {feb.conversion.rate:.1%}")
```

### Quick single-metric check

When you only need one number, use the individual methods to minimize API
calls:

```python
from sonnys_data_client import SonnysClient

with SonnysClient(api_id="your-api-id", api_key="your-api-key",
                   site_code="JOLIET") as client:
    # Just need revenue? 1 API call
    sales = client.stats.total_sales("2026-01-01", "2026-01-31")
    print(f"Revenue: ${sales.total:.2f}")

    # Just need wash count? 3 API calls
    washes = client.stats.total_washes("2026-01-01", "2026-01-31")
    print(f"Washes: {washes.total}")
```

## Performance Tips

!!! tip "Use `report()` when you need multiple KPIs"
    Calling `total_sales()`, `total_washes()`, `new_memberships_sold()`, and
    `conversion_rate()` individually duplicates bulk data fetches and plan sale
    verification calls.  The `report()` method shares all data across KPIs:

    1. `transactions.list_v2()` -- enriched transactions with membership flags
    2. `transactions.list_by_type("wash")` -- identifies actual car washes
    3. `transactions.list_by_type("recurring")` -- identifies recharges to exclude
    4. `transactions.get()` x ~N -- verifies each plan sale candidate (~15/day)

!!! tip "Use individual methods for single metrics"
    If you only need one stat, calling the individual method is more efficient
    than `report()`. For example, `total_sales()` makes just **1 API call**,
    while `report()` always makes 3 + ~N.

!!! warning "Clock entry API cost"
    Fetching clock entries requires **1 employee list call** plus
    **N_employees x ceil(days/14) clock entry calls**. For 20 employees over
    31 days, that is 1 + 20 x 3 = **61 API calls**. Use `report()` when you
    need labor data alongside other KPIs -- it shares the clock entry fetch
    with all other computations. For labor-only queries,
    `total_labor_cost()` is sufficient and avoids the extra transaction
    fetches.

!!! note "No caching between calls"
    Stats methods do not cache results between calls. Each invocation fetches
    fresh data from the API. If you need the same stats multiple times, store
    the result in a variable rather than calling the method again.
