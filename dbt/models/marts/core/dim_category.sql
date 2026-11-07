{{ config(materialized='table') }}

select distinct
    cast(category_id as int64) as category_key,
    cast(category_id as int64) as category_id,
    category_name
from {{ ref('stg_videos') }}
where category_id is not null
