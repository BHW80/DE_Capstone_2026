{{ config(materialized='table') }}

with date_spine as (
    select distinct trending_date as full_date
    from {{ ref('stg_videos') }}
    where trending_date is not null
)

select
    cast(format_date('%Y%m%d', full_date) as int64) as date_key,
    full_date,
    extract(year from full_date) as year,
    extract(month from full_date) as month,
    format_date('%B', full_date) as month_name,
    extract(day from full_date) as day,
    extract(dayofweek from full_date) as day_of_week,
    format_date('%A', full_date) as day_name,
    case when extract(dayofweek from full_date) in (1, 7) then true else false end as is_weekend
from date_spine
