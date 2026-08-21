# Intermediate models

Reusable deduplication, provider mapping, lifecycle, shared-filter, and ranking
logic. These models bridge source-specific staging data and product marts.

Implemented models:

- `int_content`: one canonical metadata row per TMDB content identity;
- `int_streaming_events`: normalized append-only lifecycle semantics;
- `int_current_availability`: TMDB-discovered current subscription catalog,
  enriched with known `new` dates;
- `int_upcoming_availability`: latest future or date-unknown announcements that
  are not already in the current catalog.
