select * from {{ ref('int_current_availability') }}
union all
select * from {{ ref('int_upcoming_availability') }}
