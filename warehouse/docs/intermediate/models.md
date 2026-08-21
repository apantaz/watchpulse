{% docs int_content %}

## Canonical content

Selects one metadata observation for each content identity, independent of
region and provider. TMDB is always preferred; embedded Streaming Availability
metadata is used only when a lifecycle title has not yet been discovered by
TMDB. It is the metadata join surface for downstream availability models.

Grain: one row per `tmdb_id + content_type`.

{% enddocs %}

{% docs int_streaming_events %}

## Normalized streaming events

Applies lifecycle semantics to deduplicated source events, defaults the MVP's
known subscription monetization type, and exposes one comparable effective
timestamp. Event history remains append-only.

Grain: one row per `event_id`.

{% enddocs %}

{% docs int_current_availability %}

## Current availability

Represents the current subscription catalog discovered through TMDB for each
region and provider. Matching `new` lifecycle events enrich `available_since`;
they do not determine whether the title is currently available.

Grain: one row per content, region, provider, and monetization type.

{% enddocs %}

{% docs int_upcoming_availability %}

## Upcoming availability

Selects the latest upcoming announcement for each availability grain and
excludes titles already present in the current TMDB catalog. Future-dated and
date-unknown announcements are retained; dated announcements in the past are
excluded.

Grain: one row per content, region, provider, and monetization type.

{% enddocs %}
