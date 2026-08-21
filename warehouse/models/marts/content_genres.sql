with flattened as (
    select
        content.tmdb_id,
        content.content_type,
        try_cast(genre.value as integer) as genre_id
    from {{ ref('int_content') }} as content,
        json_each(content.genre_ids) as genre
    where content.genre_ids is not null
)

select
    flattened.tmdb_id,
    flattened.content_type,
    flattened.genre_id,
    reference.genre_name
from flattened
left join {{ ref('genre_reference') }} as reference
    on flattened.content_type = reference.content_type
    and flattened.genre_id = reference.genre_id
where flattened.genre_id is not null
