select
    mapping.provider_key,
    mapping.source,
    mapping.source_provider_id,
    mapping.region
from {{ ref('provider_source_reference') }} as mapping
inner join {{ ref('dim_provider') }} as provider
    on mapping.provider_key = provider.provider_key
