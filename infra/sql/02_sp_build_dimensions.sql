-- =============================================================================
-- BigQuery Stored Procedure: sp_build_dimensions
-- Datei: infra/sql/02_sp_build_dimensions.sql
-- Zweck: Baut alle 3 Kimball-Dimensionstabellen auf:
--        1. dim_category (Conformed Dimension)
--        2. dim_date     (Kalender-Dimension inkl. is_weekend)
--        3. dim_video    (SCD-2 Dimension mit LEAD()-Window-Timeline fuer alle
--                         historischen Titel-Mutationen, z.B. 2kyS6SvSYSE)
-- =============================================================================
BEGIN
  -- 1. Conformed Dimension: dim_category
  CREATE OR REPLACE TABLE `cloudanalytics-514018.youtube_analytics.dim_category` AS
  SELECT DISTINCT
    CAST(category_id AS INT64) AS category_key,
    CAST(category_id AS INT64) AS category_id,
    category_name
  FROM `cloudanalytics-514018.youtube_analytics.stg_videos`
  WHERE category_id IS NOT NULL;

  -- 2. Kalender-Dimension: dim_date
  CREATE OR REPLACE TABLE `cloudanalytics-514018.youtube_analytics.dim_date` AS
  WITH date_spine AS (
    SELECT DISTINCT trending_date AS full_date
    FROM `cloudanalytics-514018.youtube_analytics.stg_videos`
    WHERE trending_date IS NOT NULL
  )
  SELECT
    CAST(FORMAT_DATE('%Y%m%d', full_date) AS INT64) AS date_key,
    full_date,
    EXTRACT(YEAR FROM full_date) AS year,
    EXTRACT(MONTH FROM full_date) AS month,
    FORMAT_DATE('%B', full_date) AS month_name,
    EXTRACT(DAY FROM full_date) AS day,
    EXTRACT(DAYOFWEEK FROM full_date) AS day_of_week,
    FORMAT_DATE('%A', full_date) AS day_name,
    CASE WHEN EXTRACT(DAYOFWEEK FROM full_date) IN (1, 7) THEN TRUE ELSE FALSE END AS is_weekend
  FROM date_spine;

  -- 3. SCD-2 Dimension: dim_video (mit lueckenloser LEAD()-Versionshistorie)
  CREATE OR REPLACE TABLE `cloudanalytics-514018.youtube_analytics.dim_video` AS
  WITH version_groups AS (
    SELECT
      video_id,
      title,
      channel_title,
      category_id,
      tags,
      MIN(trending_date) AS version_start_date
    FROM `cloudanalytics-514018.youtube_analytics.stg_videos`
    GROUP BY video_id, title, channel_title, category_id, tags
  ),
  scd2_timeline AS (
    SELECT
      TO_HEX(MD5(CONCAT(video_id, '_', CAST(version_start_date AS STRING)))) AS video_key,
      video_id,
      title,
      channel_title,
      category_id,
      tags,
      CAST(version_start_date AS TIMESTAMP) AS valid_from,
      LEAD(CAST(version_start_date AS TIMESTAMP)) OVER (
        PARTITION BY video_id
        ORDER BY version_start_date ASC
      ) AS valid_to
    FROM version_groups
  )
  SELECT
    video_key,
    video_id,
    title,
    channel_title,
    category_id,
    tags,
    valid_from,
    valid_to,
    CASE WHEN valid_to IS NULL THEN TRUE ELSE FALSE END AS is_current
  FROM scd2_timeline;

  -- 4. Conformed Dimension: dim_creator_contract (Multi-Source CRM Ingestion aus GCS)
  CREATE OR REPLACE EXTERNAL TABLE `cloudanalytics-514018.youtube_analytics.ext_creator_contracts`
  OPTIONS (
    format = 'PARQUET',
    uris = ['gs://lakehouse-youtube-cloudanalytics-514018/bronze/crm_contracts/*.parquet']
  );

  CREATE OR REPLACE TABLE `cloudanalytics-514018.youtube_analytics.dim_creator_contract` AS
  SELECT
    TO_HEX(MD5(channel_title)) AS contract_key,
    contract_id,
    channel_title,
    partner_tier,
    revenue_share_pct,
    country_code,
    account_manager,
    contract_status,
    SAFE.PARSE_DATE('%Y-%m-%d', signed_date) AS signed_date,
    CURRENT_TIMESTAMP() AS _dwh_loaded_at
  FROM `cloudanalytics-514018.youtube_analytics.ext_creator_contracts`;
END;
