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

{% docs stg_streaming_links %}

## Verified streaming deep-link staging

Extracts HTTPS title links from retained Streaming Availability change
responses and maps source service IDs to stable WatchPulse provider keys.
Removed events are excluded so an explicitly removed option cannot supply a
current destination.

Grain: one row per content, region, provider, monetization type, event type,
and event timestamp.

{% enddocs %}

{% docs stg_streaming_shows %}

## Streaming show metadata staging

Extracts the latest title metadata embedded in retained Streaming Availability
change pages. This model is a fallback for lifecycle titles that have not yet
been discovered by TMDB; it does not replace TMDB as the preferred metadata
source. Source ratings and signed image URLs are intentionally excluded.

Grain: one row per `tmdb_id + content_type`.

{% enddocs %}
