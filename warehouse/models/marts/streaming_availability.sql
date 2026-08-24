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
