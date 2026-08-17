# Warehouse

Planned `dbt-duckdb` project for `v0.3`.

Ownership:

- read immutable source data from `data/lake`;
- build staging, intermediate, and mart models;
- enforce the contracts in `docs/data-model.md`;
- build a candidate DuckDB file and publish it only after tests pass.

This component must not call external APIs.
