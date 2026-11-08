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

# 5. Der Serverless Cloud Workflow (Nutzt den existierenden Service Account)
resource "google_workflows_workflow" "youtube_dataops_pipeline" {
  name            = "youtube-dataops-pipeline"
  region          = var.region
  description     = "Serverlose Orchestrierung für YouTube DWH Star-Schema & Quality Gates"
  service_account = var.service_account_email
  source_contents = file("${path.module}/workflows/pipeline.yaml")
}
