# Changelog

All notable changes to `sonnys-data-client` are documented in this file.

## 1.7.0

### Fixed

- **`load_job()` no longer crashes on an empty result.** When a site has no
  transactions in the requested window the API returns
  `{"status": "pass", "offset": null, "limit": null, "total": null}`.
  `dict.get("total", default)` does not fall back when the key is present and
  null, so `(total + limit - 1) // limit` raised
  `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'`. Any
  site/day with no sales killed the whole export. `load_job()` now returns `[]`.

- **`RateLimiter.acquire()` is thread-safe.** It was a check-then-append race,
  so threads sharing one client could exceed the window. All mutating paths
  (`acquire`, `reset`, `available`) now hold a lock.

- **A request that had to wait is now counted.** `_request()` sleeps for the
  returned wait and then sends *without* calling `acquire()` again, so the
  request was never recorded and the window drifted over budget.

### Changed

- **Default rate limit is now 18 requests / 15 s (was 20).** The server allows
  exactly 20 — the 21st request in a window returns 429 — so targeting 20 left
  no margin for clock skew or jitter and made 429s routine in sustained batch
  use. A single-threaded two-day `load_job()` run produced 17 retry-backoff
  events before this change. Pass `RateLimiter(max_requests=20)` explicitly to
  restore the old behaviour.
## 1.6.0

### Added

- **`exclude_ecomm` flag on conversion metrics.** `client.stats.conversion_rate()`,
  `client.stats.new_memberships_sold()`, and `client.stats.report()` now accept
  a keyword-only `exclude_ecomm` parameter (default `False`). When set to
  `True`, membership sign-ups made on an E-Comm (online) terminal are excluded
  from the new-membership count (the conversion *numerator*). E-Comm terminals
  are identified by the `"E-Comm"` marker in the transaction's `salesDeviceName`
  (matched case-insensitively), which is present on every site's online
  terminal. This isolates *in-lane* conversion performance from online sign-ups.
- The exclusion adds **no extra API calls**: `salesDeviceName` is read from the
  transaction detail record that is already fetched to verify each plan sale.

### Notes

- The conversion **denominator** (eligible washes) is intentionally left
  unchanged by `exclude_ecomm`, because E-Comm terminals do not perform in-lane
  car washes — so online activity does not inflate the wash count. The flag
  therefore only affects the numerator and the resulting rate.
- Backwards compatible: existing call sites and the default behavior are
  unchanged (online sign-ups are still counted unless `exclude_ecomm=True`).

## 1.5.1

### Fixed

- `client.stats.total_washes()` and `client.stats.report()` no longer
  over-count wash volume by misclassifying prepaid sales (gift cards,
  prepaid membership purchases) and other non-wash transactions as
  retail washes. The previous logic had an "unknown non-negative type"
  fallback that swept in any v2 transaction that wasn't tagged as
  `type=wash` or `type=recurring`. A v2 transaction is now only counted
  as a wash if it is a recurring redemption, a recurring plan sale that
  also appears in `type=wash`, or itself appears in `type=wash`. Verified
  against the BackOffice "Sales Overview V2 Report" *Total Cars* figure
  on FRVW for 2026-05-06 (15 total / 2 net cars; previously the client
  returned 21 / 7).

### Changed

- `client.stats.total_washes()` now makes 2 bulk API calls (was 3) — the
  `type=recurring` fetch was load-bearing only for the removed fallback
  branch and is no longer needed. By extension, `conversion_rate()`,
  `cost_per_car()`, and `report()` each make one fewer bulk call.

## 1.5.0

### Fixed

- `Transaction` (and `TransactionJobItem`, which extends it) now coerces
  the API's empty-string sentinel to `None` for optional string fields:
  `customer_name`, `customer_id`, `vehicle_license_plate`,
  `employee_cashier`, and `employee_greeter`. The upstream API returns
  `""` instead of `null` when these fields are unset (e.g. a transaction
  with no greeter assigned), which broke `x is None` checks. Truthiness
  checks (`if txn.employee_greeter:`) were already correct and continue
  to work.

## 1.4.1

### Fixed

- `client.backoffice.timeclock()` no longer raises
  ``BackOfficeScrapeError`` when the requested date range has zero
  clock entries. BackOffice renders a single "No clock entries found
  matching the given criteria." sentinel in that case; the scraper
  now detects it and returns an empty
  :class:`BackOfficeTimeclockResult` (empty ``employees`` list, all
  totals ``0.0``, ``period_start`` / ``period_end`` echo the caller's
  requested range).

## 1.4.0

### Added

- **BackOffice scraper (`client.backoffice.timeclock()`).** A new
  resource that logs in to the Sonny's BackOffice web UI and scrapes
  the `/report/employee-timesheets` page for per-shift, per-employee
  timeclock data. On multi-site operators this is orders of magnitude
  faster than `client.stats.total_labor_cost()` because the report
  renders every employee across every site in a single HTTP round
  trip, with no published rate limit to contend with.
- New init parameters: `backoffice_username` and `backoffice_password`
  (both keyword-only, both optional). The existing `api_id` doubles as
  the BackOffice subdomain, so no new subdomain parameter is needed.
- New response models: `TimesheetShift`, `EmployeeTimesheet`,
  `BackOfficeTimeclockResult` (exposed from the top-level package).
- `TimesheetShift.is_open` property — `True` when the employee was
  still on the clock at the moment the report was rendered
  (`date_out` / `time_out` are `None` for open shifts). Partial
  hours and wages accumulated so far are still populated and rolled
  up into the employee and period totals.
- New exception classes: `BackOfficeError`, `BackOfficeCredentialsError`,
  `BackOfficeLoginError`, `BackOfficeScrapeError` (all inherit from
  `SonnysError`).
- `beautifulsoup4` added to core dependencies (~1MB, no native deps).
- Full docs guide at `docs/guides/backoffice.md` covering credentials,
  method signature, return types, open shifts, errors, and performance.

### Fixed

- `tests/test_client.py::test_429_backoff_timing` updated to match the
  2s/4s/6s retry delays introduced in 1.3.1 (the test was still
  asserting the old 1s/2s/4s values).

### Backwards compatibility

- All existing `SonnysClient(api_id, api_key, ...)` call sites
  continue to work without changes. Any attempt to call a BackOffice
  method on a client that was constructed without BackOffice
  credentials raises `BackOfficeCredentialsError` with a message
  naming the missing field(s).

