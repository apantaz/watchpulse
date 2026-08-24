select
    event_id,
    tmdb_id,
    content_type,
    region,
    provider_key,
    coalesce(monetization_type, 'subscription') as monetization_type,
    event_type,
    event_date,
    available_from,
    expires_on,
    case
        when event_type = 'upcoming' then coalesce(available_from, event_date)
        else event_date
    end as event_effective_at,
    source,
    source_event_id,
    ingested_at,
    watch_url
from {{ ref('stg_streaming_events') }}
