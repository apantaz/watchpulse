# Mart models

Normalized dimensions/facts and API-friendly serving models, including
`catalog_availability`.

- `dim_provider` owns stable provider keys and display names.
- `catalog_availability` combines current and upcoming availability with title
  metadata for local application queries.
- `catalog_freshness` exposes build time, latest source time, and validated row
  counts for the published catalog.
- `dim_content` publishes canonical title metadata.
- `content_genres` normalizes genre arrays for filtering.
- `provider_source_map` isolates upstream provider identifiers.
- `streaming_availability` publishes current and upcoming state.
- `streaming_events` publishes retained lifecycle history.
