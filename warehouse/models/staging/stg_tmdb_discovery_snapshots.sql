{% set lake_root = var('lake_root', '../data/lake') %}

with manifests as (
    select
        cast(fetched_at as timestamptz) as completed_at,
        cast(payload as json) as payload
    from read_parquet(
        '{{ lake_root }}/raw/source=tmdb/endpoint=discovery_manifest/entity_type=catalog/country=ALL/date=*/*.parquet',
        union_by_name = true
    )
),

queries as (
    select
        json_extract_string(payload, '$.run_id') as run_id,
        completed_at,
        upper(json_extract_string(query.value, '$.country')) as region,
        json_extract_string(query.value, '$.provider_key') as provider_key,
        json_extract_string(query.value, '$.content_type') as content_type,
        try_cast(json_extract_string(query.value, '$.upstream_total_pages') as integer)
            as upstream_total_pages,
        try_cast(json_extract_string(query.value, '$.expected_pages') as integer)
            as expected_pages,
        try_cast(json_extract_string(query.value, '$.pages_fetched') as integer)
            as pages_fetched,
        try_cast(json_extract_string(query.value, '$.total_results') as integer)
            as total_results,
        coalesce(try_cast(json_extract_string(query.value, '$.complete') as boolean), false)
            as is_complete,
        coalesce(
            try_cast(json_extract_string(query.value, '$.truncated_by_source_limit') as boolean),
            false
        ) as truncated_by_source_limit
    from manifests, json_each(payload, '$.queries') as query
)

select *
from queries
