provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = file(var.credentials_file)
}

# 1. Google Cloud Storage (GCS) Bucket für das Medallion Lakehouse & Iceberg
resource "google_storage_bucket" "lakehouse_storage" {
  name                        = "lakehouse-youtube-${var.project_id}"
  location                    = var.location
  force_destroy               = true # Erlaubt terraform destroy das Löschen auch bei Testdaten
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

# 2. Google BigQuery Dataset
resource "google_bigquery_dataset" "youtube_analytics" {
  dataset_id                 = "youtube_analytics"
  friendly_name              = "YouTube Video Analytics DWH"
  description                = "Zentrales DWH Dataset für Staging, SCD-2 Snapshots und Kimball Marts"
  location                   = var.location
  delete_contents_on_destroy = true # Für 0-€ Kostensicherheit bei terraform destroy
}

# 3. Google Cloud Pub/Sub: Ingest Topic & Subscription (Ersetzt lokales Kafka im Cloud-Betrieb v2.1)
resource "google_pubsub_topic" "youtube_ingest" {
  name = "topic-youtube-ingest"
}

resource "google_pubsub_subscription" "youtube_ingest_sub" {
  name                 = "sub-youtube-ingest"
  topic                = google_pubsub_topic.youtube_ingest.name
  ack_deadline_seconds = 20
}

# 4. Google Cloud Pub/Sub: Dead Letter Queue (DLQ) Topic & Subscription
resource "google_pubsub_topic" "youtube_dlq" {
  name = "topic-youtube-dlq"
}

resource "google_pubsub_subscription" "youtube_dlq_sub" {
  name                 = "sub-youtube-dlq"
  topic                = google_pubsub_topic.youtube_dlq.name
  ack_deadline_seconds = 20
}

# 5. BigQuery Stored Procedures (Pattern B: Saubere SQL-Auslagerung in infra/sql/*.sql)
resource "google_bigquery_routine" "sp_build_stg_videos" {
  dataset_id      = google_bigquery_dataset.youtube_analytics.dataset_id
  routine_id      = "sp_build_stg_videos"
  routine_type    = "PROCEDURE"
  language        = "SQL"
  description     = "Erzeugt den idempotenten, deduplizierten Staging-View stg_videos"
  definition_body = file("${path.module}/sql/01_sp_build_stg_videos.sql")
}

resource "google_bigquery_routine" "sp_build_dimensions" {
  dataset_id      = google_bigquery_dataset.youtube_analytics.dataset_id
  routine_id      = "sp_build_dimensions"
  routine_type    = "PROCEDURE"
  language        = "SQL"
  description     = "Baut dim_category, dim_date und die SCD-2 Dimension dim_video (inkl. LEAD-Timeline) auf"
  definition_body = file("${path.module}/sql/02_sp_build_dimensions.sql")
}

resource "google_bigquery_routine" "sp_refresh_fact_table" {
  dataset_id      = google_bigquery_dataset.youtube_analytics.dataset_id
  routine_id      = "sp_refresh_fact_table"
  routine_type    = "PROCEDURE"
  language        = "SQL"
  description     = "Baut fact_video_metrics mittels Point-in-Time SCD-2 Join gegen dim_video auf"
  definition_body = file("${path.module}/sql/03_sp_refresh_fact_table.sql")
}

# 6. Der Serverless Cloud Workflow (Nutzt den existierenden Service Account)
resource "google_workflows_workflow" "youtube_dataops_pipeline" {
  name            = "youtube-dataops-pipeline"
  region          = var.region
  description     = "Serverlose Orchestrierung für YouTube DWH Star-Schema & Quality Gates"
  service_account = var.service_account_email
  source_contents = file("${path.module}/workflows/pipeline.yaml")
  depends_on = [
    google_bigquery_routine.sp_build_stg_videos,
    google_bigquery_routine.sp_build_dimensions,
    google_bigquery_routine.sp_refresh_fact_table
  ]
}

# 7. Google Cloud Scheduler: Täglicher automatischer Trigger für den Cloud Workflow
resource "google_cloud_scheduler_job" "pipeline_schedule" {
  name             = "schedule-youtube-dataops-pipeline"
  description      = "Startet die YouTube DataOps Pipeline täglich um 06:00 Uhr"
  schedule         = "0 6 * * *"
  time_zone        = "Europe/Berlin"
  region           = var.region
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/workflows/${google_workflows_workflow.youtube_dataops_pipeline.name}/executions"

    oauth_token {
      service_account_email = var.service_account_email
    }
  }

  depends_on = [
    google_workflows_workflow.youtube_dataops_pipeline
  ]
}
