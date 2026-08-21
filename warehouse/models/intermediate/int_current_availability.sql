with additions as (
    select
        tmdb_id,
        content_type,
        region,
        provider_key,
        monetization_type,
        max(event_effective_at) as available_since,
        max(ingested_at) as event_ingested_at
    from {{ ref('int_streaming_events') }}
    where event_type = 'new'
    group by 1, 2, 3, 4, 5
)

select
    discovery.tmdb_id,
    discovery.content_type,
    discovery.region,
    discovery.provider_key,
    'subscription' as monetization_type,
    additions.available_since,
    cast(null as timestamptz) as available_from,
    cast(null as timestamptz) as expires_on,
    true as is_available,
    false as is_upcoming,
    'tmdb_discovery' as source,
    greatest(
        discovery.source_updated_at,
        coalesce(additions.event_ingested_at, discovery.source_updated_at)
    ) as last_updated_at
from {{ ref('stg_tmdb_discovery') }} as discovery
left join additions
    on discovery.tmdb_id = additions.tmdb_id
    and discovery.content_type = additions.content_type
    and discovery.region = additions.region
    and discovery.provider_key = additions.provider_key
    and additions.monetization_type = 'subscription'
