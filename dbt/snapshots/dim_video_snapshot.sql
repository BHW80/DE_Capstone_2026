{% snapshot dim_video_snapshot %}

{{
    config(
      target_schema='youtube_analytics',
      strategy='check',
      unique_key='video_id',
      check_cols=['title', 'channel_title', 'category_id', 'tags'],
      invalidate_hard_deletes=True
    )
}}

select
    video_id,
    title,
    channel_title,
    category_id,
    tags
from {{ ref('stg_videos') }}
qualify row_number() over (partition by video_id order by trending_date desc, _ingested_at desc) = 1

{% endsnapshot %}
