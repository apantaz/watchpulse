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
arrival, and expiration ordering. Public section routes layer their fixed
business rules onto this engine in the next increments.
