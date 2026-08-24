{% set lake_root = var('lake_root', '../data/lake') %}

with raw_responses as (
    select
        cast(fetched_at as timestamptz) as fetched_at,
        cast(request_params as json) as request_params,
        cast(payload as json) as payload
    from read_parquet(
        '{{ lake_root }}/raw/source=streaming_availability/endpoint=changes_*/entity_type=*/country=*/date=*/*.parquet',
        hive_partitioning = false,
        union_by_name = true
    )
),

expanded_changes as (
    select
        raw_responses.fetched_at,
        upper(json_extract_string(raw_responses.request_params, '$.country')) as region,
        change.value as change,
        raw_responses.payload
    from raw_responses,
        json_each(raw_responses.payload, '$.changes') as change
),

normalized as (
    select
        cast(regexp_extract(
            json_extract_string(
                payload,
                '$.shows.' || json_extract_string(change, '$.showId') || '.tmdbId'
            ),
            '[^/]+/([0-9]+)',
            1
        ) as bigint) as tmdb_id,
        case json_extract_string(change, '$.showType')
            when 'movie' then 'movie'
            when 'series' then 'tv'
        end as content_type,
        region,
        json_extract_string(change, '$.service.id') as source_provider_id,
        json_extract_string(change, '$.streamingOptionType') as monetization_type,
        json_extract_string(change, '$.changeType') as event_type,
        case
            when json_extract_string(change, '$.timestamp') is not null
                then to_timestamp(cast(json_extract_string(change, '$.timestamp') as bigint))
        end as event_date,
        json_extract_string(change, '$.link') as watch_url,
        fetched_at
    from expanded_changes
)

select
    normalized.tmdb_id,
    normalized.content_type,
    normalized.region,
    mapping.provider_key,
    normalized.monetization_type,
    normalized.event_type,
    normalized.event_date,
    normalized.watch_url,
    normalized.fetched_at
from normalized
inner join {{ ref('provider_source_reference') }} as mapping
    on normalized.source_provider_id = mapping.source_provider_id
    and normalized.region = mapping.region
    and mapping.source = 'streaming_availability'
where normalized.tmdb_id is not null
    and normalized.content_type is not null
    and normalized.watch_url like 'https://%'
    and normalized.event_type <> 'removed'
qualify row_number() over (
    partition by
        normalized.tmdb_id,
        normalized.content_type,
        normalized.region,
        mapping.provider_key,
        normalized.monetization_type,
        normalized.event_type,
        normalized.event_date
    order by normalized.fetched_at desc, normalized.watch_url
) = 1
