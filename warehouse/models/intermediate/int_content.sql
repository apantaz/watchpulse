with ranked as (
    select
        *,
        row_number() over (
            partition by tmdb_id, content_type
            order by source_updated_at desc, region, provider_key, source_file
        ) as observation_rank,
        min(source_updated_at) over (
            partition by tmdb_id, content_type
        ) as first_observed_at,
        max(source_updated_at) over (
            partition by tmdb_id, content_type
        ) as last_observed_at
    from {{ ref('stg_tmdb_discovery') }}
)

select
    tmdb_id,
    content_type,
    title,
    original_title,
    overview,
    release_date,
    genre_ids,
    original_language,
    tmdb_rating,
    vote_count,
    tmdb_popularity,
    poster_path,
    backdrop_path,
    first_observed_at,
    last_observed_at as source_updated_at
from ranked
where observation_rank = 1
