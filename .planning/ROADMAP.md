# Roadmap: Sonny's Data Client

## Milestones

- ✅ **v1.0 Initial Release** — [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) (Phases 1-10, shipped 2026-02-10)
- ✅ **v1.1 Documentation** — [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) (Phases 11-18, shipped 2026-02-11)
- ✅ **v1.2 Improvements** — [milestones/v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md) (Phases 19-26, shipped 2026-02-11)
- 🚧 **v1.3 Labor CPC** — Phases 27-34 (in progress)

### 🚧 v1.3 Labor CPC (In Progress)

**Milestone Goal:** Add labor cost per car (CPC) metric to the Stats resource, using employee clock entry data from the Sonny's API to compute labor costs and divide by total washes.

#### Phase 27: Labor Data Layer
**Goal**: Bulk-fetch clock entries across all active employees for a date range, with site filtering
**Depends on**: Previous milestone complete
**Research**: Unlikely (existing Employee resource already supports clock entries)
**Plans**: TBD

Plans:
- [x] 27-01: build_date_chunks TDD (date range splitter)
- [x] 27-02: bulk clock entry fetching

#### Phase 28: Labor Cost Result Models
**Goal**: Pydantic models for labor cost and CPC results (LaborCostResult, CostPerCarResult)
**Depends on**: Phase 27
**Research**: Unlikely (established Pydantic model patterns)
**Plans**: TBD

Plans:
- [x] 28-01: LaborCostResult and CostPerCarResult models

#### Phase 29: Labor Cost Computation
**Goal**: `total_labor_cost()` stats method computing regular + overtime cost from clock entries
**Depends on**: Phase 28
**Research**: Unlikely (internal computation, established stats patterns)
**Plans**: TBD

Plans:
- [x] 29-01: total_labor_cost() implementation + package exports

#### Phase 30: CPC Computation
**Goal**: `cost_per_car()` stats method: labor cost / total washes with zero-division safety
**Depends on**: Phase 29
**Research**: Unlikely (mirrors existing conversion_rate pattern)
**Plans**: TBD

Plans:
- [ ] 30-01: TBD

#### Phase 31: Report Integration
**Goal**: Add labor CPC to `StatsReport` and `report()` method with shared data fetching
**Depends on**: Phase 30
**Research**: Unlikely (extending existing report() pattern)
**Plans**: TBD

Plans:
- [ ] 31-01: TBD

#### Phase 32: Stats Guide Update
**Goal**: Document labor CPC methods with examples, field tables, and performance tips
**Depends on**: Phase 31
**Research**: Unlikely (following existing stats guide format)
**Plans**: TBD

Plans:
- [ ] 32-01: TBD

#### Phase 33: Unit Tests
**Goal**: Tests for labor cost aggregation and CPC calculation
**Depends on**: Phase 31
**Research**: Unlikely (established test patterns)
**Plans**: TBD

Plans:
- [ ] 33-01: TBD

#### Phase 34: Validation & Deployment
**Goal**: Validate against real JOLIET data, deploy docs to GitHub Pages
**Depends on**: Phase 32, Phase 33
**Research**: Unlikely (established validation and deployment workflow)
**Plans**: TBD

Plans:
- [ ] 34-01: TBD

## Completed Milestones

### v1.0: Initial Release — SHIPPED 2026-02-10

Complete Python SDK wrapping the Sonny's Carwash Controls Data API with 8 resource types, auto-pagination, rate limiting, batch jobs, and pip-installable distribution.

**Stats:** 10 phases, 17 plans, 34 files, 3,783 LOC Python
**Archive:** [.planning/milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

<details>
<summary>Phases (all complete)</summary>

- [x] **Phase 1: Project Foundation** - Package scaffolding, SonnysClient class, dependency declarations
- [x] **Phase 2: HTTP Transport & Errors** - Request/response cycle, auth headers, exception hierarchy, error mapping
- [x] **Phase 3: Rate Limiting** - Per-instance sliding window, 429 backoff, retry logic
- [x] **Phase 4: Response Models** - Pydantic v2 models for all 8 resource types
- [x] **Phase 5: Resource Framework** - Base resource class, list/get patterns, auto-pagination
- [x] **Phase 6: Standard Resources** - Customers, Items, Employees, Sites
- [x] **Phase 7: Account Resources** - Giftcards, Washbooks, Recurring accounts
- [x] **Phase 8: Transaction Resources** - All transaction endpoints (list, by type, detail, v2)
- [x] **Phase 9: Batch Job System** - load-job, get-job-data, auto-polling
- [x] **Phase 10: Packaging & Distribution** - pip-install from GitHub, logging polish, integration tests

</details>

### v1.1: Documentation — SHIPPED 2026-02-11

Comprehensive documentation suite — expanded README, auto-generated API reference on GitHub Pages, per-resource usage guides, and complete docstring coverage.

**Stats:** 8 phases, 16 plans, 72 files, 4,068 LOC docs + docstrings
**Archive:** [.planning/milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

<details>
<summary>Phases (all complete)</summary>

- [x] **Phase 11: README Overhaul** (2/2 plans) — completed 2026-02-10
- [x] **Phase 12: API Reference Setup** (2/2 plans) — completed 2026-02-10
- [x] **Phase 13: Resource Guides** (2/2 plans) — completed 2026-02-10
- [x] **Phase 14: Transaction Deep Dive** (2/2 plans) — completed 2026-02-11
- [x] **Phase 15: Account Resources Guide** (1/1 plan) — completed 2026-02-11
- [x] **Phase 16: Error Handling & Troubleshooting** (2/2 plans) — completed 2026-02-11
- [x] **Phase 17: Advanced Patterns** (2/2 plans) — completed 2026-02-11
- [x] **Phase 18: Docstring Audit** (3/3 plans) — completed 2026-02-11

</details>

### v1.2: Improvements — SHIPPED 2026-02-11

Client-side business analytics via `client.stats.*` — six stat methods with typed result models, efficient shared data fetching, and comprehensive documentation.

**Stats:** 8 phases, 9 plans, 35 files, 3,393 LOC added
**Archive:** [.planning/milestones/v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)

<details>
<summary>Phases (all complete)</summary>

- [x] **Phase 19: Stats Module Foundation** (2/2 plans) — completed 2026-02-11
- [x] **Phase 20: Data Fetching Layer** (1/1 plan) — completed 2026-02-11
- [x] **Phase 21: Revenue & Sales Stats** (1/1 plan) — completed 2026-02-11
- [x] **Phase 22: Wash Analytics** (1/1 plan) — completed 2026-02-11
- [x] **Phase 23: Membership Analytics** (1/1 plan) — completed 2026-02-11
- [x] **Phase 24: Conversion Rate** (1/1 plan) — completed 2026-02-11
- [x] **Phase 25: Stats Report** (1/1 plan) — completed 2026-02-11
- [x] **Phase 26: Stats Documentation & Testing** (1/1 plan) — completed 2026-02-11

</details>

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. Project Foundation | v1.0 | 1/1 | Complete | 2026-02-10 |
| 2. HTTP Transport & Errors | v1.0 | 2/2 | Complete | 2026-02-10 |
| 3. Rate Limiting | v1.0 | 2/2 | Complete | 2026-02-10 |
| 4. Response Models | v1.0 | 3/3 | Complete | 2026-02-10 |
| 5. Resource Framework | v1.0 | 1/1 | Complete | 2026-02-10 |
| 6. Standard Resources | v1.0 | 2/2 | Complete | 2026-02-10 |
| 7. Account Resources | v1.0 | 2/2 | Complete | 2026-02-10 |
| 8. Transaction Resources | v1.0 | 2/2 | Complete | 2026-02-10 |
| 9. Batch Job System | v1.0 | 1/1 | Complete | 2026-02-10 |
| 10. Packaging & Distribution | v1.0 | 1/1 | Complete | 2026-02-10 |
| 11. README Overhaul | v1.1 | 2/2 | Complete | 2026-02-10 |
| 12. API Reference Setup | v1.1 | 2/2 | Complete | 2026-02-10 |
| 13. Resource Guides | v1.1 | 2/2 | Complete | 2026-02-10 |
| 14. Transaction Deep Dive | v1.1 | 2/2 | Complete | 2026-02-11 |
| 15. Account Resources Guide | v1.1 | 1/1 | Complete | 2026-02-11 |
| 16. Error & Troubleshoot | v1.1 | 2/2 | Complete | 2026-02-11 |
| 17. Advanced Patterns | v1.1 | 2/2 | Complete | 2026-02-11 |
| 18. Docstring Audit | v1.1 | 3/3 | Complete | 2026-02-11 |
| 19. Stats Module Foundation | v1.2 | 2/2 | Complete | 2026-02-11 |
| 20. Data Fetching Layer | v1.2 | 1/1 | Complete | 2026-02-11 |
| 21. Revenue & Sales Stats | v1.2 | 1/1 | Complete | 2026-02-11 |
| 22. Wash Analytics | v1.2 | 1/1 | Complete | 2026-02-11 |
| 23. Membership Analytics | v1.2 | 1/1 | Complete | 2026-02-11 |
| 24. Conversion Rate | v1.2 | 1/1 | Complete | 2026-02-11 |
| 25. Stats Report | v1.2 | 1/1 | Complete | 2026-02-11 |
| 26. Stats Documentation & Testing | v1.2 | 1/1 | Complete | 2026-02-11 |
| 27. Labor Data Layer | v1.3 | 2/2 | Complete | 2026-02-12 |
| 28. Labor Cost Result Models | v1.3 | 1/1 | Complete | 2026-02-12 |
| 29. Labor Cost Computation | v1.3 | 1/1 | Complete | 2026-02-12 |
| 30. CPC Computation | v1.3 | 0/? | Not started | - |
| 31. Report Integration | v1.3 | 0/? | Not started | - |
| 32. Stats Guide Update | v1.3 | 0/? | Not started | - |
| 33. Unit Tests | v1.3 | 0/? | Not started | - |
| 34. Validation & Deployment | v1.3 | 0/? | Not started | - |
