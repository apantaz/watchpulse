{% docs watchpulse_warehouse %}

# WatchPulse warehouse

The WatchPulse warehouse converts immutable TMDB and Streaming Availability
Parquet data into typed, tested DuckDB objects. External APIs never run during
a dbt build. Availability objects are always scoped by region and provider.

{% enddocs %}

{% docs stg_tmdb_discovery %}

## TMDB discovery staging

Flattens raw TMDB discovery pages and selects the latest observation for every
title, content type, region, and provider. It provides basic discovery metadata
but does not claim official lifecycle dates or contain enriched title details.

Grain: one row per `tmdb_id + content_type + region + provider_key`.

{% enddocs %}

{% docs stg_streaming_events %}

## Streaming lifecycle event staging

Reads normalized, append-only streaming lifecycle events and retains the latest
physical observation for each deterministic event ID. Upcoming events remain
distinct from current availability.

Grain: one row per `event_id`.

{% enddocs %}
