{{ config(materialized='table') }}

with source_data as (
    select * from {{ ref('stg_videos') }}
),

dim_v as (
    select * from {{ ref('dim_video') }}
),

dim_c as (
    select * from {{ ref('dim_category') }}
),

dim_d as (
    select * from {{ ref('dim_date') }}
)

select
    to_hex(md5(concat(s.video_id, '_', cast(s.trending_date as string)))) as metric_key,
    dim_v.video_key,
    dim_c.category_key,
    dim_d.date_key,
    s.views,
    s.likes,
    s.dislikes,
    s.comment_count,
    safe_divide(s.likes + s.dislikes + s.comment_count, s.views) as interaction_ratio,
    s._ingested_at
from source_data s
inner join dim_v 
    on s.video_id = dim_v.video_id
    and s.trending_date >= cast(dim_v.valid_from as date)
    and (dim_v.valid_to is null or s.trending_date < cast(dim_v.valid_to as date))
left join dim_c
    on cast(s.category_id as int64) = dim_c.category_key
left join dim_d
    on cast(format_date('%Y%m%d', s.trending_date) as int64) = dim_d.date_key
