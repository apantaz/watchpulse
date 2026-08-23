# API

Read-only FastAPI discovery backend for `v0.4`.

Ownership:

- validate typed global filters;
- build safe parameterized DuckDB queries;
- expose providers, discovery sections, content details, and freshness;
- return WatchPulse-owned response models.

The API must not call external catalog sources or write to the warehouse.

## Foundation

The first increment provides process health, catalog freshness, generated
OpenAPI documentation, and a repository that opens the atomically published
DuckDB database in read-only mode.

From the repository root, run:

```bash
make dbt-publish
uvicorn watchpulse.api:create_app --factory --reload
```

The default database is `data/warehouse_serving.duckdb`. Override it with
`WATCHPULSE_SERVING_DB_PATH`. If that setting lives only in `.env`, add
`--env-file .env` to the Uvicorn command. Available foundation routes are:

- `GET /health` — process liveness; it remains available when the catalog is not;
- `GET /api/v1/catalog/freshness` — warehouse/source timestamps and row counts;
- `GET /api/v1/catalog/regions` — regions present in the published catalog;
- `GET /api/v1/catalog/providers?region=GR` — region-aware provider choices;
- `GET /api/v1/catalog/genres?region=GR` — genres scoped by optional provider/type;
- `GET /api/v1/catalog/filter-options?region=GR` — scoped types, languages, and ranges;
- `GET /api/v1/discovery/top-10?region=GR&providers=netflix` — ranked current titles;
- `GET /api/v1/discovery/new-releases?region=GR&providers=netflix` — recent releases;
- `GET /api/v1/discovery/recently-added?region=GR&providers=netflix` — provider additions;
- `GET /api/v1/discovery/upcoming?region=GR&providers=netflix` — future arrivals;
- `GET /api/v1/discovery/leaving-soon?region=GR&providers=netflix` — known expirations;
- `GET /api/v1/discovery/titles/movie/634649?region=GR&providers=netflix` — title details;
- `GET /docs` — interactive OpenAPI documentation.

Catalog failures return HTTP 503 without exposing filesystem paths or DuckDB
implementation details.

## Global discovery filters

Every discovery section will bind the same validated query contract:

| Query parameter | Required | Meaning |
|---|---:|---|
| `region` | yes | ISO alpha-2 region, normalized to uppercase |
| `providers` | yes | One or more repeated stable provider keys |
| `content_type` | no | `movie` or `tv` |
| `genre_ids` | no | One or more repeated positive TMDB genre IDs |
| `runtime_max` | no | Maximum runtime in minutes |
| `release_year_from` | no | Inclusive lower release-year bound |
| `release_year_to` | no | Inclusive upper release-year bound |
| `rating_min` | no | Minimum TMDB rating from 0 through 10 |
| `language` | no | Two- or three-letter original-language code |

Repeated parameters use standard query syntax, for example:

```text
?region=GR&providers=netflix&providers=disney_plus&genre_ids=18&genre_ids=35
```

Codes and keys are normalized, duplicate providers/genres are removed, unknown
parameters are rejected, and invalid ranges return HTTP 422 before a database
query can run.

## Shared query engine

Discovery sections use one controlled query builder over
`main_marts.catalog_availability`. User values, pagination, provider lists, and
genre lists are always bound parameters. Availability state and sorting use
closed enums mapped to fixed SQL fragments. Results are grouped to one title
with all matching selected-provider availability records attached.

Multiple selected providers or genres match any value within that category;
different filter categories must all match. The engine supports current,
upcoming, or combined state plus controlled popularity, release, addition,
arrival, and expiration ordering. Each public section route layers its fixed
business rules onto this engine; Top 10 is the first implemented section.

### Top 10

Top 10 is WatchPulse's ranking, not an upstream provider's official chart. The
initial route selects only currently available titles, applies the complete
global filter contract, sorts by TMDB popularity with deterministic tie-breaks,
and returns at most ten results. Each result has an explicit rank and aggregates
matching availability across the selected providers.

```text
GET /api/v1/discovery/top-10?region=GR&providers=netflix&content_type=movie
```

### New Releases

New Releases means recently released content, not content recently added to a
provider. The route selects currently available titles whose `release_date` is
between the response's `as_of` date minus `NEW_RELEASE_DAYS` and `as_of`, then
orders the results by release date. The response exposes the effective date and
window so clients can describe the section honestly.

```text
GET /api/v1/discovery/new-releases?region=GR&providers=netflix
```

### Recently Added

Recently Added means content newly added to a selected provider, regardless of
the content's original release date. The route selects currently available rows
whose non-null `available_since` timestamp falls within
`RECENTLY_ADDED_DAYS`, orders the newest provider additions first, and exposes
the effective timestamp/window in its response. It never substitutes
`release_date` when lifecycle evidence is missing.

```text
GET /api/v1/discovery/recently-added?region=GR&providers=netflix
```

### Upcoming

Upcoming selects only rows marked upcoming and not currently available, with a
non-null `available_from` strictly later than the response's `as_of` timestamp.
Results are ordered by earliest arrival. The route does not impose an arbitrary
future window; its bounded response returns the next 20 matching titles.

```text
GET /api/v1/discovery/upcoming?region=GR&providers=netflix
```

### Leaving Soon

Leaving Soon selects currently available rows whose non-null `expires_on`
timestamp falls between the response's `as_of` timestamp and
`LEAVING_SOON_DAYS` later, ordered by nearest expiration. WatchPulse never
infers an expiration when lifecycle evidence is absent.

The first-release ingestion policy requests only `new` and `upcoming`, so this
route currently returns an honest empty list for the retained catalog. It will
begin returning results when `expiring` ingestion is deliberately enabled.

```text
GET /api/v1/discovery/leaving-soon?region=GR&providers=netflix
```

### Title details

Title details use the canonical TMDB ID plus the explicit `movie` or `tv`
content type, region, and at least one selected provider. The response contains
normalized local metadata and aggregates matching current or upcoming
availability across those providers. A title outside that scoped catalog
returns HTTP 404; the lookup never falls back to a live upstream request.

```text
GET /api/v1/discovery/titles/movie/634649?region=GR&providers=netflix
```
