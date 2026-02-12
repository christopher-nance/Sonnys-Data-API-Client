---
phase: 28-labor-cost-models
plan: 01
subsystem: stats
tags: [pydantic, models, labor-cost, cost-per-car, stats]

# Dependency graph
requires:
  - phase: 19-stats-foundation
    provides: SonnysModel base class, _stats.py module, types/__init__.py exports
  - phase: 27-labor-data-layer
    provides: ClockEntry model with regular_rate, regular_hours, overtime_rate, overtime_hours fields
provides:
  - LaborCostResult model for total_labor_cost() return type
  - CostPerCarResult model for cost_per_car() return type
affects: [29-labor-cost-computation, 30-cpc-computation, 31-report-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [labor cost result model with 7 aggregation fields, CPC result model with zero-division safety]

key-files:
  created: []
  modified:
    - src/sonnys_data_client/types/_stats.py
    - src/sonnys_data_client/types/__init__.py
    - tests/test_types.py

key-decisions:
  - "LaborCostResult includes both cost and hours breakdowns (regular vs overtime) plus entry_count for transparency"
  - "CostPerCarResult stores component values (total_labor_cost, total_washes) alongside computed cost_per_car"

patterns-established:
  - "Labor analytics result models follow same SonnysModel pattern as SalesResult/WashResult/ConversionResult"

issues-created: []

# Metrics
duration: 6min
completed: 2026-02-12
---

# Phase 28 Plan 01: Labor Cost Result Models Summary

**LaborCostResult (7 fields) and CostPerCarResult (3 fields) Pydantic models added to stats types with Google-style docstrings**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-12T15:26:45Z
- **Completed:** 2026-02-12T15:33:03Z
- **Tasks:** 2 (+ 1 deviation fix)
- **Files modified:** 3

## Accomplishments
- `LaborCostResult` model with 7 fields: total_cost, regular_cost, overtime_cost, regular_hours, overtime_hours, total_hours, entry_count
- `CostPerCarResult` model with 3 fields: cost_per_car, total_labor_cost, total_washes
- Both models exported from `sonnys_data_client.types` and listed in `__all__`
- All 137 tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add LaborCostResult and CostPerCarResult to _stats.py** - `af8decf` (feat)
2. **Task 2: Export new models from types/__init__.py** - `51939b3` (feat)

## Files Created/Modified
- `src/sonnys_data_client/types/_stats.py` - Added LaborCostResult and CostPerCarResult models before StatsReport
- `src/sonnys_data_client/types/__init__.py` - Added imports and __all__ entries for both new models
- `tests/test_types.py` - Updated __all__ count assertion from 34 to 36

## Decisions Made
None - followed plan as specified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated __all__ count assertion in test_types.py**
- **Found during:** Task 2 (Export new models)
- **Issue:** `test_all_has_34_models` hard-coded expected count of 34 entries in `__all__`, failed with 36 after adding two new models
- **Fix:** Updated assertion from 34 to 36
- **Files modified:** tests/test_types.py
- **Verification:** All 137 tests pass
- **Committed in:** `46b5cec`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to keep test suite green. No scope creep.

## Issues Encountered
None

## Next Phase Readiness
- Phase 28 (Labor Cost Result Models) complete — single plan executed
- LaborCostResult ready for `total_labor_cost()` computation in Phase 29
- CostPerCarResult ready for `cost_per_car()` computation in Phase 30
- Ready for Phase 29: Labor Cost Computation

---
*Phase: 28-labor-cost-models*
*Completed: 2026-02-12*
