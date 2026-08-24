with latest_announcements as (
    select
        *,
        row_number() over (
            partition by tmdb_id, content_type, region, provider_key, monetization_type
            order by ingested_at desc, event_effective_at desc nulls last, event_id
        ) as announcement_rank
    from {{ ref('int_streaming_events') }}
    where event_type = 'upcoming'
),

current_availability as (
    select *
    from {{ ref('int_current_availability') }}
)

select
    upcoming.tmdb_id,
    upcoming.content_type,
    upcoming.region,
    upcoming.provider_key,
    upcoming.monetization_type,
    cast(null as timestamptz) as available_since,
    upcoming.event_effective_at as available_from,
    cast(null as timestamptz) as expires_on,
    upcoming.watch_url,
    false as is_available,
    true as is_upcoming,
    upcoming.source,
    upcoming.ingested_at as last_updated_at
from latest_announcements as upcoming
left join current_availability as current
    on upcoming.tmdb_id = current.tmdb_id
    and upcoming.content_type = current.content_type
    and upcoming.region = current.region
    and upcoming.provider_key = current.provider_key
    and upcoming.monetization_type = current.monetization_type
where upcoming.announcement_rank = 1
    and current.tmdb_id is null
    and (
        upcoming.event_effective_at is null
        or upcoming.event_effective_at > current_timestamp
    )
