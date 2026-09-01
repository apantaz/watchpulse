with tmdb_metadata_candidates as (
    select
        tmdb_id,
        content_type,
        title,
        original_title,
        overview,
        release_date,
        year(release_date)::integer as release_year,
        runtime_minutes,
        episode_count,
        season_count,
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
    from {{ ref('stg_tmdb_metadata') }}
),

tmdb_candidates as (
    select
        tmdb_id,
        content_type,
        title,
        original_title,
        overview,
        release_date,
        year(release_date)::integer as release_year,
        cast(null as integer) as runtime_minutes,
        cast(null as integer) as episode_count,
        cast(null as integer) as season_count,
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
        2 as source_priority
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
        cast(null as integer) as episode_count,
        cast(null as integer) as season_count,
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
        3 as source_priority
    from {{ ref('stg_streaming_shows') }}
),

candidates as (
    select * from tmdb_metadata_candidates
    union all
    select * from tmdb_candidates
    union all
    select * from streaming_candidates
),

latest_tmdb_volatile_fields as (
    select
        tmdb_id,
        content_type,
        arg_max(tmdb_rating, source_updated_at)
            filter (where tmdb_rating is not null) as tmdb_rating,
        arg_max(vote_count, source_updated_at)
            filter (where vote_count is not null) as vote_count,
        arg_max(tmdb_popularity, source_updated_at)
            filter (where tmdb_popularity is not null) as tmdb_popularity
    from candidates
    where metadata_source = 'tmdb'
    group by 1, 2
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
),

selected as (
    select *
    from ranked
    where observation_rank = 1
)

select
    selected.tmdb_id,
    selected.content_type,
    selected.title,
    selected.original_title,
    selected.overview,
    selected.release_date,
    selected.release_year,
    selected.runtime_minutes,
    selected.episode_count,
    selected.season_count,
    selected.genre_ids,
    selected.original_language,
    coalesce(volatile.tmdb_rating, selected.tmdb_rating) as tmdb_rating,
    coalesce(volatile.vote_count, selected.vote_count) as vote_count,
    coalesce(volatile.tmdb_popularity, selected.tmdb_popularity) as tmdb_popularity,
    selected.poster_path,
    selected.backdrop_path,
    selected.metadata_source,
    selected.first_observed_at,
    selected.last_observed_at as source_updated_at
from selected
left join latest_tmdb_volatile_fields as volatile
    using (tmdb_id, content_type)
