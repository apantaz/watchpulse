{% set lake_root = var('lake_root', '../data/lake') %}

with raw_records as (
    select
        filename as source_file,
        cast(fetched_at as timestamptz) as fetched_at,
        cast(request_params as json) as request_params,
        cast(payload as json) as payload
    from read_parquet(
        '{{ lake_root }}/raw/source=tmdb/endpoint=metadata/entity_type=*/country=ALL/date=*/*.parquet',
        filename = true,
        hive_partitioning = false,
        union_by_name = true
    )
),

normalized as (
    select
        cast(json_extract_string(request_params, '$.tmdb_id') as bigint) as tmdb_id,
        json_extract_string(request_params, '$.entity_type') as content_type,
        coalesce(
            json_extract_string(payload, '$.title'),
            json_extract_string(payload, '$.name')
        ) as title,
        coalesce(
            json_extract_string(payload, '$.original_title'),
            json_extract_string(payload, '$.original_name')
        ) as original_title,
        nullif(json_extract_string(payload, '$.overview'), '') as overview,
        try_cast(coalesce(
            json_extract_string(payload, '$.release_date'),
            json_extract_string(payload, '$.first_air_date')
        ) as date) as release_date,
        try_cast(json_extract_string(payload, '$.runtime') as integer) as movie_runtime,
        try_cast(json_extract_string(payload, '$.episode_run_time[0]') as integer) as series_runtime,
        try_cast(json_extract_string(payload, '$.number_of_episodes') as integer) as episode_count,
        try_cast(json_extract_string(payload, '$.number_of_seasons') as integer) as season_count,
        json_extract(payload, '$.genres') as genres,
        json_extract_string(payload, '$.original_language') as original_language,
        try_cast(json_extract_string(payload, '$.vote_average') as double) as tmdb_rating,
        coalesce(try_cast(json_extract_string(payload, '$.vote_count') as bigint), 0) as vote_count,
        try_cast(json_extract_string(payload, '$.popularity') as double) as tmdb_popularity,
        json_extract_string(payload, '$.poster_path') as poster_path,
        json_extract_string(payload, '$.backdrop_path') as backdrop_path,
        fetched_at as source_updated_at,
        source_file
    from raw_records
)

select
    tmdb_id,
    content_type,
    title,
    original_title,
    overview,
    release_date,
    coalesce(nullif(movie_runtime, 0), nullif(series_runtime, 0)) as runtime_minutes,
    episode_count,
    season_count,
    to_json(list_transform(cast(genres as json[]), genre -> cast(json_extract_string(genre, '$.id') as integer))) as genre_ids,
    original_language,
    tmdb_rating,
    vote_count,
    tmdb_popularity,
    poster_path,
    backdrop_path,
    source_updated_at,
    source_file
from normalized
where tmdb_id is not null and content_type in ('movie', 'tv')
qualify row_number() over (
    partition by tmdb_id, content_type
    order by source_updated_at desc, source_file desc
) = 1
