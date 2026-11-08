{{ config(materialized='table') }}

with version_groups as (
    select
        video_id,
        title,
        channel_title,
        category_id,
        tags,
        min(trending_date) as version_start_date
    from {{ ref('stg_videos') }}
    group by video_id, title, channel_title, category_id, tags
),

scd2_timeline as (
    select
        to_hex(md5(concat(video_id, '_', cast(version_start_date as string)))) as video_key,
        video_id,
        title,
        channel_title,
        category_id,
        tags,
        cast(version_start_date as timestamp) as valid_from,
        lead(cast(version_start_date as timestamp)) over (
            partition by video_id order by version_start_date asc
        ) as valid_to
    from version_groups
)

select
    video_key,
    video_id,
    title,
    channel_title,
    category_id,
    tags,
    valid_from,
    valid_to,
    case when valid_to is null then true else false end as is_current
from scd2_timeline
