# API

Planned read-only discovery backend for `v0.4`.

Ownership:

- validate typed global filters;
- build safe parameterized DuckDB queries;
- expose providers, discovery sections, content details, and freshness;
- return WatchPulse-owned response models.

The API must not call external catalog sources or write to the warehouse.
