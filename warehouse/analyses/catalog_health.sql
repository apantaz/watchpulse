select 'tmdb_provider_title_rows' as metric, count(*)::bigint as metric_value
from {{ ref('stg_tmdb_discovery') }}

union all

select 'streaming_event_rows' as metric, count(*)::bigint as metric_value
from {{ ref('stg_streaming_events') }}

union all

select 'tmdb_titles_without_posters' as metric, count(*)::bigint as metric_value
from {{ ref('stg_tmdb_discovery') }}
where poster_path is null
