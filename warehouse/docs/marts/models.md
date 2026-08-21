{% docs dim_provider %}

## Provider dimension

Defines the stable, source-independent provider keys and display names exposed
to application consumers.

Grain: one row per `provider_key`.

{% enddocs %}

{% docs catalog_availability %}

## Catalog availability

Serving-ready union of current and upcoming subscription availability enriched
with canonical title metadata and stable provider names. It is built entirely
from WatchPulse-owned data and is the initial local query surface for the UI.

Current and upcoming states are mutually exclusive. TMDB metadata is preferred;
Streaming Availability metadata is used as a transparent fallback for lifecycle
titles that have not yet received TMDB enrichment.

Grain: one row per content, region, provider, and monetization type.

{% enddocs %}

{% docs catalog_freshness %}

## Catalog freshness

Records when the serving warehouse was built, the newest source observation in
the catalog, and state-level row counts. The atomic publisher validates this row
before replacing the last known-good serving database.

Grain: one row for `catalog_availability`.

{% enddocs %}

{% docs dim_content %}

## Content dimension

Publishes one canonical metadata row per TMDB content identity. TMDB metadata is
preferred, with the documented lifecycle fallback retained until enrichment.

Grain: one row per `tmdb_id + content_type`.

{% enddocs %}

{% docs content_genres %}

## Content genres

Normalizes TMDB genre arrays into filter-friendly rows with stable names scoped
by movie or TV content type.

Grain: one row per `tmdb_id + content_type + genre_id`.

{% enddocs %}

{% docs provider_source_map %}

## Provider source map

Maps source-specific provider identifiers into stable WatchPulse provider keys
without exposing upstream IDs to application consumers.

Grain: one row per provider, source, source provider ID, and region.

{% enddocs %}

{% docs streaming_availability %}

## Streaming availability

Publishes the mutually exclusive current and upcoming availability states at
the normalized region/provider/monetization grain.

Grain: one row per content, region, provider, and monetization type.

{% enddocs %}

{% docs streaming_events %}

## Streaming events

Publishes the deduplicated, append-only lifecycle event history retained by
WatchPulse.

Grain: one row per `event_id`.

{% enddocs %}
