-- =============================================================================
-- BigQuery Stored Procedure: sp_build_stg_videos
-- Datei: infra/sql/01_sp_build_stg_videos.sql
-- Zweck: Erzeugt den idempotenten, deduplizierten Staging-View stg_videos
--        auf Basis der aus GCS geladenen Tabelle silver_videos.
-- =============================================================================
BEGIN
  CREATE OR REPLACE VIEW `cloudanalytics-514018.youtube_analytics.stg_videos` AS
  SELECT
    TRIM(video_id) AS video_id,
    CAST(trending_date AS DATE) AS trending_date,
    TRIM(title) AS title,
    TRIM(channel_title) AS channel_title,
    CAST(category_id AS INT64) AS category_id,
    COALESCE(TRIM(category_name), 'Unknown') AS category_name,
    CAST(publish_time AS TIMESTAMP) AS publish_time,
    TRIM(tags) AS tags,
    CAST(views AS INT64) AS views,
    CAST(likes AS INT64) AS likes,
    CAST(dislikes AS INT64) AS dislikes,
    CAST(comment_count AS INT64) AS comment_count,
    CAST(_ingested_at AS TIMESTAMP) AS _ingested_at
  FROM `cloudanalytics-514018.youtube_analytics.silver_videos`
  WHERE video_id IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY TRIM(video_id), CAST(trending_date AS DATE)
    ORDER BY CAST(_ingested_at AS TIMESTAMP) DESC
  ) = 1;
END;
