with tmdb_candidates as (
    select
        tmdb_id,
        content_type,
        title,
        original_title,
        overview,
        release_date,
        year(release_date)::integer as release_year,
        cast(null as integer) as runtime_minutes,
        genre_ids,
        original_language,
        tmdb_rating,
        vote_count,
        tmdb_popularity,
        poster_path,
        backdrop_path,
        source_updated_at,
        source_file,
        'tmdb' as metadata_source,
        1 as source_priority
    from {{ ref('stg_tmdb_discovery') }}
),

streaming_candidates as (
    select
        tmdb_id,
        content_type,
        title,
        original_title,
        overview,
        cast(null as date) as release_date,
        release_year,
        runtime_minutes,
        cast(null as json) as genre_ids,
        cast(null as varchar) as original_language,
        cast(null as double) as tmdb_rating,
        cast(null as bigint) as vote_count,
        cast(null as double) as tmdb_popularity,
        cast(null as varchar) as poster_path,
        cast(null as varchar) as backdrop_path,
        source_updated_at,
        source_file,
        'streaming_availability' as metadata_source,
        2 as source_priority
    from {{ ref('stg_streaming_shows') }}
),

candidates as (
    select * from tmdb_candidates
    union all
    select * from streaming_candidates
),

ranked as (
    select
        *,
        row_number() over (
            partition by tmdb_id, content_type
            order by source_priority, source_updated_at desc, source_file
        ) as observation_rank,
        min(source_updated_at) over (
            partition by tmdb_id, content_type
        ) as first_observed_at,
        max(source_updated_at) over (
            partition by tmdb_id, content_type
        ) as last_observed_at
    from candidates
)

select
    tmdb_id,
    content_type,
    title,
    original_title,
    overview,
    release_date,
    release_year,
    runtime_minutes,
    genre_ids,
    original_language,
    tmdb_rating,
    vote_count,
    tmdb_popularity,
    poster_path,
    backdrop_path,
    metadata_source,
    first_observed_at,
    last_observed_at as source_updated_at
from ranked
where observation_rank = 1
