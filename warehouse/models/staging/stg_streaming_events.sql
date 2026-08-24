{% set lake_root = var('lake_root', '../data/lake') %}

with events as (
    select
        cast(event_id as varchar) as event_id,
        cast(tmdb_id as bigint) as tmdb_id,
        cast(content_type as varchar) as content_type,
        upper(cast(region as varchar)) as region,
        cast(provider_key as varchar) as provider_key,
        cast(monetization_type as varchar) as monetization_type,
        cast(event_type as varchar) as event_type,
        cast(event_date as timestamptz) as event_date,
        cast(available_from as timestamptz) as available_from,
        cast(expires_on as timestamptz) as expires_on,
        cast(source as varchar) as source,
        cast(source_event_id as varchar) as source_event_id,
        cast(ingested_at as timestamptz) as ingested_at
    from read_parquet(
        '{{ lake_root }}/events/source=streaming_availability/region=*/date=*/*.parquet',
        hive_partitioning = false,
        union_by_name = true
    )
),

links as (
    select * from {{ ref('stg_streaming_links') }}
)

select
    events.*,
    links.watch_url
from events
left join links
    on events.tmdb_id = links.tmdb_id
    and events.content_type = links.content_type
    and events.region = links.region
    and events.provider_key = links.provider_key
    and events.monetization_type = links.monetization_type
    and events.event_type = links.event_type
    and events.event_date is not distinct from links.event_date
qualify row_number() over (
    partition by events.event_id
    order by events.ingested_at desc
) = 1
