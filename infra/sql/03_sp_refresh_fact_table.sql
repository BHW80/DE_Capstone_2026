-- =============================================================================
-- BigQuery Stored Procedure: sp_refresh_fact_table
-- Datei: infra/sql/03_sp_refresh_fact_table.sql
-- Zweck: Baut die zentrale Faktentabelle fact_video_metrics mittels
--        Point-in-Time SCD-2 Join gegen dim_video auf.
-- =============================================================================
BEGIN
  CREATE OR REPLACE TABLE `cloudanalytics-514018.youtube_analytics.fact_video_metrics` AS
  SELECT
    TO_HEX(MD5(CONCAT(s.video_id, '_', CAST(s.trending_date AS STRING)))) AS metric_key,
    dim_v.video_key,
    CAST(s.category_id AS INT64) AS category_key,
    CAST(FORMAT_DATE('%Y%m%d', s.trending_date) AS INT64) AS date_key,
    s.views,
    s.likes,
    s.dislikes,
    s.comment_count,
    SAFE_DIVIDE(s.likes + s.dislikes + s.comment_count, s.views) AS interaction_ratio,
    s._ingested_at
  FROM `cloudanalytics-514018.youtube_analytics.stg_videos` s
  INNER JOIN `cloudanalytics-514018.youtube_analytics.dim_video` dim_v
    ON s.video_id = dim_v.video_id
    AND s.trending_date >= CAST(dim_v.valid_from AS DATE)
    AND (dim_v.valid_to IS NULL OR s.trending_date < CAST(dim_v.valid_to AS DATE));
END;
