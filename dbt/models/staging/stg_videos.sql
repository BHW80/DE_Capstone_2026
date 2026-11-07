with source as (
    select * from {{ source('youtube_raw', 'silver_videos') }}
)

select
    trim(video_id) as video_id,
    cast(trending_date as date) as trending_date,
    trim(title) as title,
    trim(channel_title) as channel_title,
    cast(category_id as int64) as category_id,
    coalesce(trim(category_name), 'Unknown') as category_name,
    cast(publish_time as timestamp) as publish_time,
    trim(tags) as tags,
    cast(views as int64) as views,
    cast(likes as int64) as likes,
    cast(dislikes as int64) as dislikes,
    cast(comment_count as int64) as comment_count,
    cast(_ingested_at as timestamp) as _ingested_at
from source
where video_id is not null
