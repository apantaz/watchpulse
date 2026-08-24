with additions as (
    select
        tmdb_id,
        content_type,
        region,
        provider_key,
        monetization_type,
        max(event_effective_at) as available_since,
        max(ingested_at) as event_ingested_at,
        arg_max(watch_url, ingested_at) filter (where watch_url is not null) as watch_url
    from {{ ref('int_streaming_events') }}
    where event_type = 'new'
    group by 1, 2, 3, 4, 5
),

current_sources as (
    select
        tmdb_id,
        content_type,
        region,
        provider_key,
        'subscription' as monetization_type,
        source_updated_at,
        'tmdb_discovery' as source
    from {{ ref('stg_tmdb_discovery') }}

    union all

    select
        tmdb_id,
        content_type,
        region,
        provider_key,
        monetization_type,
        source_updated_at,
        'tmdb_watch_providers' as source
    from {{ ref('stg_tmdb_watch_providers') }}
),

current_availability as (
    select
        *,
        row_number() over (
            partition by tmdb_id, content_type, region, provider_key, monetization_type
            order by source_updated_at desc, source
        ) as source_rank
    from current_sources
)

select
    current.tmdb_id,
    current.content_type,
    current.region,
    current.provider_key,
    current.monetization_type,
    additions.available_since,
    cast(null as timestamptz) as available_from,
    cast(null as timestamptz) as expires_on,
    additions.watch_url,
    true as is_available,
    false as is_upcoming,
    current.source,
    greatest(
        current.source_updated_at,
        coalesce(additions.event_ingested_at, current.source_updated_at)
    ) as last_updated_at
from current_availability as current
left join additions
    on current.tmdb_id = additions.tmdb_id
    and current.content_type = additions.content_type
    and current.region = additions.region
    and current.provider_key = additions.provider_key
    and current.monetization_type = additions.monetization_type
where current.source_rank = 1
