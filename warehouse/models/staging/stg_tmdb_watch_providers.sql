{% set lake_root = var('lake_root', '../data/lake') %}

with raw as (
    select
        cast(request_params as json) as request_params,
        cast(payload as json) as payload,
        cast(fetched_at as timestamptz) as source_updated_at,
        filename as source_file
    from read_parquet(
        '{{ lake_root }}/raw/source=tmdb/endpoint=watch_providers/entity_type=*/country=ALL/date=*/*.parquet',
        filename = true,
        hive_partitioning = false,
        union_by_name = true
    )
),

flattened as (
    select
        cast(json_extract_string(raw.request_params, '$.tmdb_id') as bigint) as tmdb_id,
        json_extract_string(raw.request_params, '$.entity_type') as content_type,
        upper(region.key) as region,
        cast(json_extract_string(provider.value, '$.provider_id') as varchar) as source_provider_id,
        raw.source_updated_at,
        raw.source_file
    from raw,
        json_each(raw.payload, '$.results') as region,
        json_each(region.value, '$.flatrate') as provider
),

mapped as (
    select
        flattened.tmdb_id,
        flattened.content_type,
        flattened.region,
        provider.provider_key,
        'subscription' as monetization_type,
        flattened.source_updated_at,
        flattened.source_file
    from flattened
    inner join {{ ref('provider_source_reference') }} as provider
        on provider.source = 'tmdb'
        and provider.region = flattened.region
        and provider.source_provider_id = flattened.source_provider_id
)

select * exclude row_rank
from (
    select
        *,
        row_number() over (
            partition by tmdb_id, content_type, region, provider_key, monetization_type
            order by source_updated_at desc, source_file desc
        ) as row_rank
    from mapped
)
where row_rank = 1
