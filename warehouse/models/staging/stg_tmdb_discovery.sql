{% set lake_root = var('lake_root', '../data/lake') %}

with raw_pages as (
    select
        filename as source_file,
        cast(fetched_at as timestamptz) as fetched_at,
        entity_type as content_type,
        upper(country) as region,
        regexp_extract(filename, 'endpoint=discover_([^/]+)', 1) as provider_key,
        payload
    from read_parquet(
        '{{ lake_root }}/raw/source=tmdb/endpoint=discover_*/entity_type=*/country=*/date=*/*.parquet',
        filename = true,
        hive_partitioning = true,
        union_by_name = true
    )
),

flattened as (
    select
        cast(json_extract_string(result.value, '$.id') as bigint) as tmdb_id,
        content_type,
        region,
        provider_key,
        coalesce(
            json_extract_string(result.value, '$.title'),
            json_extract_string(result.value, '$.name')
        ) as title,
        coalesce(
            json_extract_string(result.value, '$.original_title'),
            json_extract_string(result.value, '$.original_name')
        ) as original_title,
        json_extract_string(result.value, '$.overview') as overview,
        try_cast(
            coalesce(
                json_extract_string(result.value, '$.release_date'),
                json_extract_string(result.value, '$.first_air_date')
            ) as date
        ) as release_date,
        json_extract(result.value, '$.genre_ids') as genre_ids,
        json_extract_string(result.value, '$.original_language') as original_language,
        try_cast(json_extract_string(result.value, '$.vote_average') as double) as tmdb_rating,
        coalesce(try_cast(json_extract_string(result.value, '$.vote_count') as bigint), 0) as vote_count,
        try_cast(json_extract_string(result.value, '$.popularity') as double) as tmdb_popularity,
        json_extract_string(result.value, '$.poster_path') as poster_path,
        json_extract_string(result.value, '$.backdrop_path') as backdrop_path,
        fetched_at as source_updated_at,
        source_file
    from raw_pages,
        json_each(json_extract(payload, '$.results')) as result
)

select *
from flattened
qualify row_number() over (
    partition by tmdb_id, content_type, region, provider_key
    order by source_updated_at desc, source_file desc
) = 1
