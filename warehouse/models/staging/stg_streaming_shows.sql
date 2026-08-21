{% set lake_root = var('lake_root', '../data/lake') %}

with raw_pages as (
    select
        filename as source_file,
        cast(fetched_at as timestamptz) as fetched_at,
        payload
    from read_parquet(
        '{{ lake_root }}/raw/source=streaming_availability/endpoint=changes_*/entity_type=show/country=*/date=*/*.parquet',
        filename = true,
        hive_partitioning = true,
        union_by_name = true
    )
),

flattened as (
    select
        try_cast(split_part(json_extract_string(show_row.value, '$.tmdbId'), '/', 2) as bigint) as tmdb_id,
        case split_part(json_extract_string(show_row.value, '$.tmdbId'), '/', 1)
            when 'movie' then 'movie'
            when 'tv' then 'tv'
        end as content_type,
        json_extract_string(show_row.value, '$.title') as title,
        json_extract_string(show_row.value, '$.originalTitle') as original_title,
        json_extract_string(show_row.value, '$.overview') as overview,
        try_cast(json_extract_string(show_row.value, '$.releaseYear') as integer) as release_year,
        try_cast(json_extract_string(show_row.value, '$.runtime') as integer) as runtime_minutes,
        json_extract(show_row.value, '$.genres') as source_genres,
        fetched_at as source_updated_at,
        source_file
    from raw_pages,
        json_each(json_extract(payload, '$.shows')) as show_row
)

select *
from flattened
where tmdb_id is not null
    and content_type is not null
qualify row_number() over (
    partition by tmdb_id, content_type
    order by source_updated_at desc, source_file desc
) = 1
