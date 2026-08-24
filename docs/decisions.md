# WatchPulse Architecture Decisions

Status: active decision log. Decisions are append-only: when a decision changes,
add a new record that supersedes the old one rather than silently rewriting
history.

## ADR-001: External APIs are ingestion-only

- Status: accepted
- Date: 2026-08-17

Decision: TMDB and the Streaming Availability API are called only by scheduled
backend ingestion. User browsing and filter changes query WatchPulse-owned data.

Why: this prevents upstream latency, outages, rate limits, and per-user traffic
from affecting normal discovery. It also makes historical availability possible.

Consequences: daily freshness rather than real-time claims; a local serving
dataset and scheduled ingestion are mandatory.

## ADR-002: Parquet plus DuckDB for the MVP

- Status: accepted
- Date: 2026-08-16

Decision: use append-only Parquet as the replayable raw lake and DuckDB for dbt
transformation and local serving.

Why: it is inexpensive, portable, simple for one developer, and strong for this
analytics-shaped workload.

Consequences: publish database files atomically and keep the API read-only.
Postgres remains the upgrade path when measured serving concurrency warrants it.

## ADR-003: TMDB owns metadata; Streaming Availability owns lifecycle

- Status: accepted
- Date: 2026-08-17

Decision: TMDB provides content identity and general metadata. The Streaming
Availability API provides new, removed, updated, expiring, and upcoming events
and current regional availability. TMDB watch providers may seed or reconcile a
catalog but are not the final lifecycle source.

Why: the two sources have different strengths, and lifecycle sections need
dates/events not reliably represented by a metadata catalog.

Consequences: provider mappings must translate both sources into stable
WatchPulse keys.

## ADR-004: Stable internal provider keys

- Status: accepted
- Date: 2026-08-17

Decision: API and frontend contracts use keys such as `netflix` and
`disney_plus`; upstream IDs remain in a source mapping model.

Why: external IDs vary between sources and can change independently of the
product contract.

Consequences: every new source/provider requires an explicit mapping and tests.

## ADR-005: New Releases differs from Recently Added

- Status: accepted
- Date: 2026-08-17

Decision: New Releases uses the content's `release_date`. Recently Added uses
provider/region `available_since` or an equivalent lifecycle event.

Why: a newly streamed library title is not a newly released production.

Consequences: both dates remain first-class and have independent configurable
windows.

## ADR-006: One shared filter universe

- Status: accepted
- Date: 2026-08-17

Decision: region, providers, type, genre, runtime, release year, rating, and
language are applied before section-specific predicates and ranking.

Why: sections otherwise become inconsistent mini-products and surprise users.

Consequences: query construction must be centralized and tested across every
section.

## ADR-007: Guest discovery requires no account

- Status: accepted
- Date: 2026-08-17

Decision: region, provider selection, filters, sections, and content details are
available anonymously. Browser-local preferences are sufficient for the MVP.

Why: authentication is not necessary to answer the core discovery question.

Consequences: login is deferred until persistent memory and personalization are
implemented.

## ADR-008: Parameterized backend queries

- Status: accepted
- Date: 2026-08-17

Decision: validated filter objects produce controlled SQL predicates and bind
parameters. Raw user SQL is never accepted or concatenated.

Why: correctness, security, and a stable serving contract.

Consequences: supported filters require explicit query-layer implementation.

## ADR-009: Replaceable ranking

- Status: accepted
- Date: 2026-08-17

Decision: Top 10 means a WatchPulse score, initially allowed to use TMDB
popularity. Ranking logic is isolated from UI and query transport.

Why: the formula will evolve as better signals become available.

Consequences: never describe it as an official provider Top 10; add versioned
ranking inputs when the formula becomes more sophisticated.

## ADR-010: Natural language is a bounded query interface

- Status: accepted for a later version
- Date: 2026-08-17

Decision: an LLM may translate a user request into structured intent. Local
catalog queries determine real availability, and unrelated prompts return an
unsupported intent.

Why: this provides conversational discovery without hallucinating provider
catalogs or becoming a general chatbot.

Consequences: backend-only model calls, request/cost limits, usage records, and
a global kill switch are prerequisites.

## ADR-011: Movie of the Night v4 for streaming lifecycle data

- Status: accepted for v0.2
- Date: 2026-08-17

Decision: use the direct Movie of the Night Streaming Availability API v4 as
the first streaming lifecycle source. Authenticate with `X-API-Key`, keep the
base URL configurable, and use `GET /changes` for region/provider-scoped `new`,
`removed`, `updated`, `expiring`, and `upcoming` events.

Why: the official contract exposes the exact lifecycle concepts WatchPulse
needs, supports ISO alpha-2 countries and subscription-only catalog selectors,
uses cursor pagination, and returns affected shows with `tmdbId` for joining to
the TMDB metadata catalog.

Consequences:

- WatchPulse must ingest at least daily and retain its own event history because
  past/future change queries are limited to a 31-day window;
- unknown future dates are valid and remain nullable;
- initial v0.2 ingestion is show-level; season/episode events are deferred;
- source service IDs are mapped to stable WatchPulse provider keys;
- the direct developer endpoint is implemented first; a RapidAPI adapter can be
  added later without changing normalized models;
- the selected account plan and quota must be verified before enabling a full
  scheduled production job.

## ADR-012: Limit first-release lifecycle ingestion to new and upcoming

- Status: accepted for the first public release
- Date: 2026-08-17
- Supersedes ADR-011 only for the default ingestion scope

Decision: the Streaming Availability client and normalized model retain support
for all five lifecycle types, but ordinary MVP runs request only `new` and
`upcoming`. Current availability comes from TMDB discovery. Removed, updated,
expiring, and the Leaving Soon section are deferred.

Why: Recently Added and Upcoming provide the clearest user value for the first
release. One page per selected type bounds an ordinary run at two requests,
while temporary stale availability is an explicitly accepted MVP limitation.

Consequences: a title removed after the last successful TMDB catalog scan may
remain visible temporarily. The UI must show its refresh time and must not claim
complete or real-time availability. Deferred lifecycle types can be enabled
explicitly without changing the source adapter or event schema.

## ADR-013: Separate TMDB catalog discovery from title enrichment

- Status: accepted for v0.3
- Date: 2026-08-21

Decision: broad TMDB provider ingestion stores discovery pages and their basic
title metadata without automatically calling full metadata and watch-provider
endpoints for every result. Per-title enrichment is explicit and will become an
incremental queue for missing, changed, or prioritized titles.

Why: discovery returns 20 titles per request and already includes the fields
needed for initial cards and ranking. Eagerly making two more calls for every
title turns a 471-page Netflix Greece scan into roughly 19,000 requests.

Consequences: discovery runs expose page/result completeness for each
region/provider/content-type query. Runtime and richer details may be null until
a title is enriched. A query truncated by TMDB's 500-page source ceiling cannot
be considered complete and must later be partitioned into smaller date ranges.

## ADR-014: TMDB-preferred metadata with lifecycle fallback

- Status: accepted for v0.3
- Date: 2026-08-21

Decision: canonical content selects TMDB metadata whenever it exists. For an
upcoming lifecycle title not yet present in TMDB discovery data, WatchPulse uses
the basic title, overview, release year, and runtime embedded in the retained
Streaming Availability response until TMDB enrichment becomes available.

Why: lifecycle announcements can precede catalog discovery. Dropping unmatched
rows would make valid upcoming titles invisible in the serving catalog.

Consequences: `metadata_source` is exposed for lineage. Streaming ratings are
not treated as TMDB ratings, temporary signed image URLs are excluded, and
source genres remain unmapped until a normalized genre dimension exists.

## ADR-015: Replace the genre seed with ingested TMDB reference data

- Status: accepted for a later ingestion increment
- Date: 2026-08-21

Decision: the v0.3 `genre_reference.csv` seed is a bootstrap reference, not the
permanent genre source of truth. A later scheduled job will ingest TMDB genre
definitions into immutable raw Parquet, followed by `stg_tmdb_genres` and a
historically observable `dim_genre`. `content_genres` will continue to expand
title genre arrays locally and join them to that dimension.

Why: new combinations of known genre IDs already require no maintenance, but a
new ID, a new content-type/ID pairing, or a renamed genre should be detected and
tracked without requiring a code release or manual seed edit.

Consequences:

- store `first_observed_at`, `last_observed_at`, and the latest genre name;
- alert on new IDs, content-type pairings, and renamed labels;
- retain the last successfully published genre dimension when ingestion fails;
- keep a strict unknown-genre test so incomplete candidates cannot be published;
- retain the seed only as a bootstrap/fallback fixture once ingestion exists.

## ADR-016: Use FastAPI behind a read-only catalog repository

- Status: accepted for v0.4
- Date: 2026-08-21

Decision: the discovery backend uses a FastAPI application factory and accesses
the atomically published DuckDB database through a repository boundary. Each
repository connection is read-only. Liveness does not depend on catalog
availability, while catalog-dependent endpoints return HTTP 503 when the
published database is missing or unreadable.

Why: FastAPI provides typed validation and generated OpenAPI documentation with
little framework code. The application factory keeps tests isolated, and the
repository prevents DuckDB details from becoming part of the HTTP contract.

Consequences: normal browsing never calls upstream APIs or writes to the
warehouse. The repository can later target a different serving database without
changing endpoint response models. Deployment must provide a readable published
database through `WATCHPULSE_SERVING_DB_PATH`.

## ADR-017: Use one controlled discovery query engine

- Status: accepted for v0.4
- Date: 2026-08-23

Decision: every discovery section uses one `DiscoveryFilters` contract and one
query builder. Availability state and ordering are controlled enums mapped to
fixed SQL expressions. All filter values, limits, and offsets are DuckDB bound
parameters. A title available through multiple selected providers is returned
once with the matching availability records aggregated beneath it.

Why: duplicating SQL per section would allow filter semantics to drift and make
region/provider leakage harder to detect. Returning one title per card avoids
forcing the frontend to understand or deduplicate the warehouse's
title/provider/monetization grain.

Consequences: providers and selected genres use OR semantics, while different
filter categories combine with AND semantics. Section-specific date predicates
and ranking remain fixed business rules layered onto the same engine. Adding a
new serving database requires replacing the repository implementation, not the
HTTP or filter contracts.

## ADR-018: React and TypeScript for the discovery frontend

- Status: accepted for v0.5
- Date: 2026-08-23

Decision: build the guest discovery interface as a React 19 single-page
application using TypeScript and Vite. The frontend owns presentation and
browser-local preferences, while all availability, filtering, and ranking stay
behind the FastAPI contract. Vitest and Testing Library cover user-visible
behavior. Production dependencies are kept deliberately small.

Why: the interface has shared filter state, five reactive discovery rails, and
title details, which benefit from component composition and typed API
contracts. Vite provides a fast development/build loop without introducing a
full-stack JavaScript server that would duplicate FastAPI responsibilities.

Consequences:

- Node.js 22 is the supported development and CI runtime;
- the browser calls only the configured WatchPulse API base URL;
- FastAPI permits an explicit environment-configured list of frontend origins;
- SEO pre-rendering remains possible later, but is not required for the local
  deterministic MVP;
- authentication, server-side rendering, and a UI component framework are not
  introduced by this decision.

## ADR-019: Expose only verified provider deep links

- Status: accepted for v0.5
- Date: 2026-08-24

Decision: provider badges may open a title on its streaming platform only when
WatchPulse retains an HTTPS `watch_url` supplied by Streaming Availability.
Links are extracted from immutable raw change payloads, scoped by content,
region, provider, and monetization type, and remain nullable throughout the
warehouse and API. TMDB-only availability does not receive a guessed link.

Why: provider search URLs and title-derived slugs are not reliable direct-title
destinations. Presenting one as authoritative would weaken the local catalog's
evidence rules and create broken or misleading navigation.

Consequences: link coverage is initially partial and improves as lifecycle
evidence is ingested. Removed events cannot supply a current destination. The
frontend renders an external link only for validated HTTPS values, opens it in
a separate tab with safe relationship attributes, and leaves other provider
badges informational.

## ADR-020: Incrementally enrich lifecycle-only titles from TMDB

Status: Accepted (2026-08-24)

Streaming lifecycle events can introduce upcoming or newly added TMDB IDs that
are absent from the current provider discovery snapshot. Embedded lifecycle
metadata may omit descriptions and does not provide TMDB poster paths.

WatchPulse extracts the stable TMDB ID from retained lifecycle data and fetches
metadata plus current watch-provider evidence in a separate bounded ingestion
command. Raw responses are stored locally. `stg_tmdb_metadata` takes precedence
over broad discovery and streaming metadata fallbacks, while targeted provider
evidence reconciles current availability with lifecycle announcements. An
already-available series may therefore be both current and upcoming; the UI
labels this as a new season without claiming a season number absent upstream.
Browser requests never trigger enrichment, and each retained response type is
skipped independently on subsequent runs.

## Open decisions

These remain unresolved and should receive new ADRs when decided:

- hosting platform and atomic DuckDB artifact delivery;
- initial public regions and providers beyond the configurable Greece default;
- measured threshold for moving serving from DuckDB to Postgres.
