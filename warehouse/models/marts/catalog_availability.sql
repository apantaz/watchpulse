with availability as (
    select current.*
    from {{ ref('int_current_availability') }} as current
    where not exists (
        select 1
        from {{ ref('int_upcoming_availability') }} as upcoming
        where upcoming.tmdb_id = current.tmdb_id
            and upcoming.content_type = current.content_type
            and upcoming.region = current.region
            and upcoming.provider_key = current.provider_key
            and upcoming.monetization_type = current.monetization_type
    )
    union all
    select * from {{ ref('int_upcoming_availability') }}
)

select
    availability.tmdb_id,
    availability.content_type,
    content.title,
    content.original_title,
    content.overview,
    content.release_date,
    content.release_year,
    content.runtime_minutes,
    content.episode_count,
    content.season_count,
    content.original_language,
    content.genre_ids,
    content.tmdb_rating,
    content.vote_count,
    content.tmdb_popularity as popularity_score,
    availability.region,
    availability.provider_key,
    provider.provider_name,
    availability.monetization_type,
    availability.available_since,
    availability.available_from,
    availability.expires_on,
    availability.watch_url,
    availability.is_available,
    availability.is_upcoming,
    content.poster_path,
    content.backdrop_path,
    content.metadata_source,
    availability.source as availability_source,
    greatest(content.updated_at, availability.last_updated_at) as last_updated_at
from availability
inner join {{ ref('dim_content') }} as content
    on availability.tmdb_id = content.tmdb_id
    and availability.content_type = content.content_type
inner join {{ ref('dim_provider') }} as provider
    on availability.provider_key = provider.provider_key
where provider.is_active
