select
    provider_key,
    provider_name,
    is_active
from {{ ref('provider_reference') }}
