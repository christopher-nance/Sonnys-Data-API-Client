# sonnys-data-API-client

> A typed Python SDK for the Sonny's Carwash Controls Data API.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Pydantic v2](https://img.shields.io/badge/pydantic-v2-green)
![License: Wash Associates Internal Use](https://img.shields.io/badge/license-Wash%20Associates%20Internal%20Use-blue)
![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-brightgreen)

`sonnys-data-client` wraps the Sonny's Carwash Controls REST API with a
resource-based interface (`client.transactions.list()`,
`client.customers.get(id)`). Every response is returned as a validated Pydantic
v2 model, list calls auto-paginate transparently, and a built-in rate limiter
with exponential-backoff retry keeps your application within the API's
20-request/15-second window.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Client Configuration](#client-configuration)
- [Resources](#resources)
  - [Customers](#customers)
  - [Items](#items)
  - [Employees](#employees)
  - [Sites](#sites)
  - [Giftcards](#giftcards)
  - [Washbooks](#washbooks)
  - [Recurring Accounts](#recurring-accounts)
  - [Transactions](#transactions)
  - [Stats](#stats)
- [Error Handling](#error-handling)
- [Logging](#logging)
- [Multi-Site Usage](#multi-site-usage)
- [Requirements](#requirements)

## Installation

```bash
pip install git+https://github.com/christopher-nance/Sonnys-Data-API-Client
```

## Quick Start

```python
from sonnys_data_client import SonnysClient

with SonnysClient(api_id="your-api-id", api_key="your-api-key") as client:
    transactions = client.transactions.list(startDate="2024-01-01", endDate="2024-01-31")
    for txn in transactions:
        print(txn.transaction_id, txn.total)
```

All resources auto-paginate by default -- calling `.list()` returns every record
across all pages.

## Client Configuration

### Constructor

```python
SonnysClient(
    api_id: str,
    api_key: str,
    site_code: str | None = None,
    *,
    max_retries: int = 3,
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_id` | `str` | *required* | Sonny's API ID credential |
| `api_key` | `str` | *required* | Sonny's API key credential |
| `site_code` | `str \| None` | `None` | Optional site code to scope all requests to a single site |
| `max_retries` | `int` | `3` | Maximum retry attempts for 429 rate-limit responses (uses exponential backoff) |

### Context Manager

Use the `with` statement to ensure the underlying HTTP session is closed
automatically when you are done:

```python
with SonnysClient(api_id="id", api_key="key") as client:
    data = client.customers.list()
```

If you prefer manual lifecycle management, call `.close()` explicitly:

```python
client = SonnysClient(api_id="id", api_key="key")
try:
    data = client.customers.list()
finally:
    client.close()
```

### Authentication

Credentials are sent as HTTP headers on every request:

- `X-Sonnys-API-ID` -- from `api_id`
- `X-Sonnys-API-Key` -- from `api_key`
- `X-Sonnys-Site-Code` -- from `site_code` (omitted when `None`)

## Resources

| Resource | Methods |
|---|---|
| `client.customers` | `list(**params)`, `get(id)` |
| `client.items` | `list(**params)` |
| `client.employees` | `list(**params)`, `get(id)`, `get_clock_entries(employee_id, *, start_date, end_date)` |
| `client.sites` | `list(**params)` |
| `client.giftcards` | `list(**params)` |
| `client.washbooks` | `list(**params)`, `get(id)` |
| `client.recurring` | `list(**params)`, `get(id)`, `list_status_changes(**params)`, `list_modifications(**params)`, `list_details(**params)` |
| `client.transactions` | `list(**params)`, `get(id)`, `list_by_type(item_type, **params)`, `list_v2(**params)`, `load_job(*, poll_interval, timeout, **params)` |
| `client.stats` | `total_sales(start, end)`, `total_washes(start, end)`, `retail_wash_count(start, end)`, `new_memberships_sold(start, end)`, `conversion_rate(start, end)`, `total_labor_cost(start, end)`, `cost_per_car(start, end)`, `report(start, end)` |

All `list()` methods auto-paginate by default -- every page is fetched
transparently and the complete result set is returned. Common query parameters
include `startDate`, `endDate`, `site`, `region`, `limit`, and `offset`.

### Customers

**Methods:** `list(**params)` | `get(id)`

```python
customers = client.customers.list(startDate="2024-01-01", endDate="2024-01-31")
for c in customers:
    print(c.customer_id, c.first_name, c.last_name, c.is_active)

# Get full detail for a single customer
detail = client.customers.get("12345")
print(detail.email, detail.phone, detail.address.city)
```

**Returns:** `list[CustomerListItem]` from `list()` -- fields include
`customer_id`, `first_name`, `last_name`, `phone_number`, `is_active`,
`created_date`. `Customer` from `get()` -- adds `email`, `address`, `company_name`,
`loyalty_number`, `birth_date`.

### Items

**Methods:** `list(**params)`

```python
items = client.items.list()
for item in items:
    print(item.sku, item.name, item.department_name, item.price_at_site)
```

**Returns:** `list[Item]` -- fields include `sku`, `name`, `department_name`,
`price_at_site`, `cost_per_item`, `is_prompt_for_price`, `site_location`.

### Employees

**Methods:** `list(**params)` | `get(id)` | `get_clock_entries(employee_id, *, start_date, end_date)`

```python
employees = client.employees.list()
for emp in employees:
    print(emp.employee_id, emp.first_name, emp.last_name)

# Get clock entries for a date range
entries = client.employees.get_clock_entries(
    42, start_date="2024-01-01", end_date="2024-01-07"
)
for entry in entries:
    print(entry.clock_in, entry.clock_out, entry.regular_hours, entry.site_code)
```

**Returns:** `list[EmployeeListItem]` from `list()` -- fields include
`employee_id`, `first_name`, `last_name`. `Employee` from `get()` -- adds
`active`, `start_date`, `phone`, `email`. `list[ClockEntry]` from
`get_clock_entries()` -- fields include `clock_in`, `clock_out`,
`regular_hours`, `overtime_hours`, `regular_rate`, `site_code`.

### Sites

**Methods:** `list(**params)`

```python
sites = client.sites.list()
for site in sites:
    print(site.site_id, site.code, site.name, site.timezone)
```

**Returns:** `list[Site]` -- fields include `site_id`, `code`, `name`,
`timezone`. Sites is non-paginated; all sites are returned in a single
request.

### Giftcards

**Methods:** `list(**params)`

```python
giftcards = client.giftcards.list(startDate="2024-01-01", endDate="2024-01-31")
for gc in giftcards:
    print(gc.giftcard_id, gc.number, gc.value, gc.amount_used, gc.site_code)
```

**Returns:** `list[GiftcardListItem]` -- fields include `giftcard_id`,
`number`, `value`, `amount_used`, `site_code`, `complete_date`.

### Washbooks

**Methods:** `list(**params)` | `get(id)`

```python
washbooks = client.washbooks.list()
for wb in washbooks:
    print(wb.id, wb.name, wb.balance, wb.status)

# Get full detail including tags and vehicles
detail = client.washbooks.get("WB-123")
print(detail.customer.first_name, detail.recurring_info.next_bill_date)
for tag in detail.tags:
    print(tag.number, tag.enabled)
```

**Returns:** `list[WashbookListItem]` from `list()` -- fields include `id`,
`name`, `balance`, `sign_up_date`, `cancel_date`, `status`, `customer_id`.
`Washbook` from `get()` -- adds `customer`, `recurring_info`, `tags`,
`vehicles`.

### Recurring Accounts

**Methods:** `list(**params)` | `get(id)` | `list_status_changes(**params)` | `list_modifications(**params)` | `list_details(**params)`

```python
accounts = client.recurring.list(startDate="2024-01-01", endDate="2024-01-31")
for acct in accounts:
    print(acct.id, acct.name, acct.status_name, acct.billing_site_code)

# Get status changes for a date range
changes = client.recurring.list_status_changes(
    startDate="2024-01-01", endDate="2024-01-31"
)
for change in changes:
    print(change.recurring_id, change.old_status, "->", change.new_status)
```

**Returns:** `list[RecurringListItem]` from `list()` -- fields include `id`,
`name`, `status_name`, `sign_up_date`, `billing_site_code`, `customer_id`.
`Recurring` from `get()` -- adds `plan_name`, `customer`, `tags`, `vehicles`,
`recurring_statuses`, `recurring_billings`. `list[RecurringStatusChange]` from
`list_status_changes()`. `list[RecurringModification]` from
`list_modifications()`. `list[Recurring]` from `list_details()` (full detail
for every account).

### Transactions

**Methods:** `list(**params)` | `get(id)` | `list_by_type(item_type, **params)` | `list_v2(**params)` | `load_job(*, poll_interval, timeout, **params)`

```python
txns = client.transactions.list(startDate="2024-01-01", endDate="2024-01-31")
for txn in txns:
    print(txn.trans_id, txn.date, txn.total)

# Filter by type: wash, prepaid-wash, recurring, washbook,
#   giftcard, merchandise, house-account
washes = client.transactions.list_by_type(
    "wash", startDate="2024-01-01", endDate="2024-01-31"
)
```

**`list_v2`** returns enriched items with extra fields -- `customer_id`,
`is_recurring_plan_sale`, `is_recurring_plan_redemption`, `transaction_status`:

```python
v2 = client.transactions.list_v2(startDate="2024-01-01", endDate="2024-01-31")
for txn in v2:
    print(txn.trans_id, txn.customer_id, txn.transaction_status)
```

**`load_job`** submits a batch job and auto-polls until results are ready.
The API caches job data for 20 minutes and limits the date range to 24 hours:

```python
results = client.transactions.load_job(
    startDate="2024-01-01",
    endDate="2024-01-01",
    poll_interval=2.0,   # seconds between poll attempts (default 2.0)
    timeout=300.0,        # max seconds to wait per job (default 300.0)
)
for item in results:
    print(item.id, item.complete_date, item.total, item.transaction_status)
```

**Returns:** `list[TransactionListItem]` from `list()` and `list_by_type()` --
fields include `trans_id`, `trans_number`, `total`, `date`.
`Transaction` from `get()` -- adds `items`, `tenders`, `discounts`,
`customer_name`, `employee_cashier`, `location_code`.
`list[TransactionV2ListItem]` from `list_v2()` -- extends list item with
`customer_id`, `is_recurring_plan_sale`, `is_recurring_plan_redemption`,
`transaction_status`. `list[TransactionJobItem]` from `load_job()` -- full
transaction detail plus v2 enrichment fields.

### Stats

**Methods:** `total_sales(start, end)` | `total_washes(start, end)` | `retail_wash_count(start, end)` | `new_memberships_sold(start, end)` | `conversion_rate(start, end)` | `total_labor_cost(start, end)` | `cost_per_car(start, end)` | `report(start, end)`

Unlike other resources that wrap REST endpoints directly, `client.stats`
computes business analytics by fetching raw data and aggregating it locally.
Calculations are designed to align with **[Rinsed: The Car Wash CRM](https://www.rinsed.co/)** reporting as closely as possible.
All methods accept a date range as ISO-8601 strings or `datetime` objects:

```python
# Individual metrics
sales = client.stats.total_sales("2026-01-01", "2026-01-31")
print(f"Revenue: ${sales.total:.2f}")

washes = client.stats.total_washes("2026-01-01", "2026-01-31")
print(f"Total washes: {washes.total}, Member: {washes.member_wash_count}")

rate = client.stats.conversion_rate("2026-01-01", "2026-01-31")
print(f"Conversion: {rate.rate:.1%}")

# Labor cost breakdown
labor = client.stats.total_labor_cost("2026-01-01", "2026-01-31")
print(f"Labor: ${labor.total_cost:.2f} ({labor.total_hours:.1f}h)")

# Cost per car
cpc = client.stats.cost_per_car("2026-01-01", "2026-01-31")
print(f"Cost per car: ${cpc.cost_per_car:.2f}")

# All KPIs in one call (4 bulk + clock entries + ~N detail calls)
rpt = client.stats.report("2026-01-01", "2026-01-31")
print(f"Revenue: ${rpt.sales.total:.2f}, Washes: {rpt.washes.total}")
print(f"New members: {rpt.new_memberships}, Conversion: {rpt.conversion.rate:.1%}")
print(f"Labor: ${rpt.labor.total_cost:.2f}, Cost/car: ${rpt.cost_per_car.cost_per_car:.2f}")
```

**Returns:** `SalesResult` from `total_sales()` -- fields include `total`,
`count`, `recurring_plan_sales`, `retail`. `WashResult` from `total_washes()`
-- fields include `total`, `retail_wash_count`, `member_wash_count`,
`eligible_wash_count`, `free_wash_count`. `int` from `retail_wash_count()` and
`new_memberships_sold()`. `ConversionResult` from `conversion_rate()` -- fields
include `rate`, `new_memberships`, `eligible_washes`. `LaborCostResult` from
`total_labor_cost()` -- fields include `total_cost`, `regular_cost`,
`overtime_cost`, `regular_hours`, `overtime_hours`, `total_hours`,
`entry_count`. `CostPerCarResult` from `cost_per_car()` -- fields include
`cost_per_car`, `total_labor_cost`, `total_washes`. `StatsReport` from
`report()` -- bundles `sales`, `washes`, `new_memberships`, `conversion`,
`labor`, `cost_per_car`, `period_start`, `period_end`.

## Error Handling

All exceptions inherit from `SonnysError`:

```python
from sonnys_data_client import SonnysClient, SonnysError, AuthError, NotFoundError

with SonnysClient(api_id="id", api_key="key") as client:
    try:
        customer = client.customers.get("12345")
    except AuthError as e:
        print("Bad credentials:", e.message)
    except NotFoundError as e:
        print("Customer not found:", e.message)
    except SonnysError as e:
        print("API error:", e)
```

Exception hierarchy:

- `SonnysError` -- base for all errors
  - `APIError` -- base for API-specific errors
    - `APIConnectionError` -- connection failure
      - `APITimeoutError` -- request timeout
    - `APIStatusError` -- HTTP error response (has `status_code`, `body`, `error_type`)
      - `AuthError` -- 403 Forbidden
      - `RateLimitError` -- 429 Too Many Requests
      - `ValidationError` -- 400 / 422 bad request
      - `NotFoundError` -- 404 Not Found
      - `ServerError` -- 500+ server errors

Rate limiting is handled automatically -- the client retries 429 responses with
exponential backoff (up to `max_retries`, default 3). A built-in rate limiter
also throttles outgoing requests to stay under the API rate limit.

## Logging

The client uses Python standard logging under the `sonnys_data_client` logger.
Enable debug output to see HTTP requests, responses, and timing:

```python
import logging

logging.getLogger("sonnys_data_client").setLevel(logging.DEBUG)
logging.basicConfig()
```

Log levels:

- **DEBUG** -- request method/path/params, response status/elapsed time, rate limiter waits
- **WARNING** -- 429 rate limit retries

## Multi-Site Usage

Instantiate separate clients for each set of credentials:

```python
from sonnys_data_client import SonnysClient

washu = SonnysClient(api_id="washu-id", api_key="washu-key")
icon = SonnysClient(api_id="icon-id", api_key="icon-key")

washu_sites = washu.sites.list()
icon_sites = icon.sites.list()

washu.close()
icon.close()
```

Use `site_code` to scope a client to a single site:

```python
client = SonnysClient(api_id="id", api_key="key", site_code="JOLIET")
```

## Requirements

- Python 3.10+
- [requests](https://docs.python-requests.org/) >= 2.28
- [pydantic](https://docs.pydantic.dev/) >= 2.10
