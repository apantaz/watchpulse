# WatchPulse Delivery Roadmap

Status: active, version-oriented plan. A version is complete only when its exit
criteria pass. Scope should move forward sequentially unless a production defect
requires a patch release.

## Versioning approach

- `v0.x` versions build and validate the MVP incrementally.
- `v1.0` is the first polished public deterministic-discovery release.
- Later minor versions add natural language and optional personalization without
  weakening the local-catalog source-of-truth rule.

Every version should include tests, documentation updates, and a short release
note describing decisions and known limitations.

## v0.1 — Foundation

Goal: create a trustworthy, configurable ingestion foundation.

Scope:

- repository structure and optional pyenv workflow;
- environment-backed configuration;
- source-independent content/provider models;
- retrying, rate-limited HTTP client;
- TMDB discovery, metadata, and watch-provider raw ingestion;
- append-only partitioned Parquet writes;
- DuckDB initialization and `pipeline_runs` metadata;
- offline unit tests.

Current status: **complete (2026-08-17)**. Configuration, models, TMDB
ingestion, Parquet writes, DuckDB run metadata, offline tests, CI, bounded
manual ingestion automation, and a live Greece smoke run are complete. The live
run finished successfully with 310 API requests/records and produced a readable
local subscription-catalog sample.

Exit criteria:

- a smoke ingestion succeeds with a valid TMDB key;
- a failed run is recorded with a sanitized error;
- reruns preserve raw history;
- normal tests make no network calls;
- setup and operation are documented.

Exit criteria result: all passed. See [v0.1 release notes](releases/v0.1.md).

## v0.2 — Streaming lifecycle ingestion

Goal: establish region/provider availability and historical events.

Current status: **complete pending merge (2026-08-17)**. Movie of the Night v4,
provider mappings, all five lifecycle types, raw/normalized event persistence,
idempotent current state, quota enforcement, replay/inspection, manual automation,
and offline tests are implemented. The first-release default now requests only
`new` and `upcoming`; the other types remain available but deferred.

Scope:

- select and document the Streaming Availability API contract;
- implement its client and adapter;
- add stable provider crosswalks;
- ingest current, new, removed, updated, expiring, and upcoming records;
- persist append-only lifecycle events;
- schedule incremental daily ingestion and reconciliation behavior;
- add fixtures and adapter/event-history tests.

Exit criteria:

- availability is always region- and provider-scoped;
- removed titles are no longer current;
- upcoming titles are not current;
- historical events survive source-window changes;
- no secrets appear in raw request metadata or logs.

Exit criteria result: lifecycle behavior passed with documented reconciliation
limitations. Automatic daily scheduling is intentionally deferred until durable
storage, monitoring, and a production API budget are available; the workflow is
manual for now.
See [v0.2 release notes](releases/v0.2.md).

First-release product decision: Recently Added uses `new`, Upcoming uses
`upcoming`, and current availability comes from TMDB discovery. Removed,
updated, expiring, and Leaving Soon are deferred; temporary stale availability
is an accepted MVP limitation.

The manual lifecycle workflow combines the four launch providers and fully
paginates `new` and `upcoming`. Automatic scheduling remains deferred.

## v0.3 — dbt and serving catalog

Goal: turn raw source data into a tested local catalog.

Current status: **complete (2026-08-21)**. The dbt-duckdb warehouse now rebuilds
tested staging, intermediate, normalized, freshness, and serving models from the
append-only Parquet lake. Atomic publication validates a candidate database
before replacing the last good serving file. The retained Greece development
data produces 160 current and 30 upcoming catalog rows across four providers.

Scope:

- initialize dbt-duckdb;
- make TMDB discovery-only the default and report scan completeness;
- build staging models for both sources;
- build `dim_content`, genres, providers, mappings, availability, and events;
- build `catalog_availability`;
- add freshness, relationship, uniqueness, and business-rule tests;
- implement build-to-temporary-file and atomic publication.

Exit criteria:

- the warehouse rebuilds from the Parquet lake;
- all documented grains and invariants are tested;
- New Release and Recently Added remain distinct;
- failed tests cannot replace the last good serving database.

Exit criteria result: all passed. `release_date` and `available_since` remain
separate warehouse concepts so New Releases and Recently Added cannot be
conflated; their section-level query rules are delivered by v0.4. See the
[v0.3 release notes](releases/v0.3.md).

## v0.4 — Backend discovery API

Goal: expose safe local discovery without upstream calls.

Current status: **in progress (2026-08-23)**. FastAPI, an application factory,
environment-backed serving-database configuration, read-only DuckDB repository,
process health, catalog freshness, safe unavailable-catalog responses, generated
OpenAPI documentation, and offline integration tests are implemented. The
shared typed filter contract now validates and normalizes region, providers,
content type, genres, runtime, release-year range, rating, and language before
any discovery query is built. Read-only reference endpoints expose catalog
regions, region-aware providers, scoped genres, content types, languages, and
useful runtime/year/rating ranges without upstream calls. One parameterized
query engine now applies the shared filter universe, controlled availability
state/sorting, safe pagination, and provider aggregation for every upcoming
discovery section. The public Top 10 endpoint now layers current-availability
and popularity rules onto that engine and exposes all global filters in OpenAPI.
New Releases independently applies the configurable content-release window to
`release_date`, explicitly excluding future releases and avoiding any use of
provider addition dates. Recently Added separately requires retained
`available_since` lifecycle evidence within `RECENTLY_ADDED_DAYS`; missing
addition timestamps are not guessed from catalog scans or content release dates.
Upcoming now returns only non-current lifecycle rows whose `available_from` is
strictly later than the response timestamp, ordered by the next known arrival.
Leaving Soon has a complete current-title/expiration-window contract but returns
an honest empty result while the first-release ingestion policy leaves
`expiring` events disabled; expiration dates are never inferred.

Scope:

- read-only DuckDB repository layer;
- typed global filter contract;
- parameterized query builder;
- provider/region options and content details;
- Top 10, New Releases, Recently Added, Leaving Soon, and Upcoming endpoints;
- freshness metadata and error handling;
- API unit and integration tests.

Exit criteria:

- all sections use the same global filters;
- region/provider leakage tests pass;
- runtime and rating boundaries are correct;
- frontend-like requests cause zero external API calls;
- OpenAPI documentation reflects the contract.

## v0.5 — Frontend discovery

Goal: deliver the complete deterministic user experience locally.

Scope:

- choose and document the frontend framework;
- region selector and region-aware provider selection;
- type, genre, runtime, release-year, and rating filters;
- responsive rails/cards for all five sections;
- title details;
- browser-local guest preferences;
- loading, empty, stale-data, and error states.

Exit criteria:

- the Definition of a Good MVP in `AGENTS.md` works end-to-end locally;
- no login is required;
- filter changes only query the WatchPulse backend;
- mobile and desktop layouts are credible for a portfolio demonstration.

## v0.6 — Automation and deployment

Goal: make WatchPulse reproducible, observable, and publicly accessible.

Scope:

- CI for formatting, linting, unit tests, and dbt build/tests;
- scheduled daily ingestion;
- atomic serving-database delivery;
- visible run status, freshness, and failure notification;
- backend/frontend deployment;
- production configuration and secret management;
- replace the bootstrap genre seed with scheduled TMDB genre-reference
  ingestion, change detection, and unknown-genre alerts;
- architecture diagram and operational documentation.

Exit criteria:

- a live URL is available;
- deployment is reproducible from the repository;
- ingestion failure is visible and leaves the last good catalog live;
- secrets remain backend-only;
- a second region is smoke-tested end-to-end.

Current status: basic Python test CI exists early; linting, dbt checks, scheduled
jobs, and deployment are added as their corresponding components become real.

## v1.0 — Public deterministic MVP

Goal: polish and stabilize the first portfolio-ready release.

Scope:

- address usability, accessibility, and reliability findings from v0.6;
- tune initial ranking while keeping it explainable and replaceable;
- complete README, architecture, data dictionary, and release notes;
- document limitations and data freshness honestly;
- establish a small regression suite for core user journeys.

Exit criteria:

- all 14 MVP outcomes in `AGENTS.md` are demonstrable;
- five discovery sections are polished rather than merely present;
- monitoring shows successful scheduled refreshes;
- a recruiter or engineer can understand and run the project.

## v1.1 — Natural-language discovery

Goal: convert bounded user intent into the existing local filter/query contract.

Prerequisites:

- deterministic discovery is stable;
- usage persistence, rate limiting, cost caps, and kill switch exist.

Scope:

- supported/unsupported intent classification;
- structured filter extraction;
- removable interpreted-filter chips;
- local candidate query and optional explanation;
- guest/authenticated limits and cost monitoring.

Exit criteria:

- the LLM never decides availability;
- unsupported prompts end after one application response;
- the rest of WatchPulse works when AI is disabled.

## v1.2+ — Optional personalization

Possible scope after evidence of need:

- optional authentication;
- saved, watched, liked, disliked, and not-interested signals;
- deterministic New For You scoring;
- persistent cross-device preferences;
- later experiments with semantic or collaborative techniques.

This work must not become a prerequisite for basic discovery.

## Version workflow

For each version:

1. Confirm scope and unresolved decisions.
2. Implement the smallest vertical increment.
3. Add unit, integration, and data tests proportional to risk.
4. Update `data-model.md` and add ADRs when contracts or decisions change.
5. Validate exit criteria.
6. Record known limitations and mark the version complete.
