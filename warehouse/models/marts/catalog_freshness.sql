select
    'catalog_availability' as catalog_name,
    current_timestamp as warehouse_built_at,
    max(last_updated_at) as latest_source_updated_at,
    count(*)::bigint as catalog_row_count,
    count_if(is_available)::bigint as current_row_count,
    count_if(is_upcoming)::bigint as upcoming_row_count
from {{ ref('catalog_availability') }}
