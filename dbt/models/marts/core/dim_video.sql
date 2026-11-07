{{ config(materialized='table') }}

select
    dbt_scd_id as video_key,
    video_id,
    title,
    channel_title,
    category_id,
    tags,
    dbt_valid_from as valid_from,
    dbt_valid_to as valid_to,
    case when dbt_valid_to is null then true else false end as is_current
from {{ ref('dim_video_snapshot') }}
