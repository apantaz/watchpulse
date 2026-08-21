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
- `GET /docs` — interactive OpenAPI documentation.

Catalog failures return HTTP 503 without exposing filesystem paths or DuckDB
implementation details.
