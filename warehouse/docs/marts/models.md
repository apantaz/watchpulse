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
