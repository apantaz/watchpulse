# Snapshots

dbt snapshots are reserved for mutable source tables that require slowly
changing history. The current Parquet event lake is already append-only, so no
snapshot is needed yet. Add snapshots here only with a documented grain,
strategy, unique key, and invalidation behavior.
