# Staging models

Typed, renamed, source-specific models that remain close to raw inputs. No
product-facing business logic belongs here.

Implemented models:

- `stg_tmdb_discovery`: latest title observation by region and provider;
- `stg_streaming_events`: lifecycle events deduplicated by deterministic ID.
