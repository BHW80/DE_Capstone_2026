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

# 3. Google Cloud Pub/Sub: Ingest Topic (Ersetzt lokales Kafka im Cloud-Betrieb)
resource "google_pubsub_topic" "youtube_ingest" {
  name = "topic-youtube-ingest"
}

# 4. Google Cloud Pub/Sub: Dead Letter Queue (DLQ) Topic
resource "google_pubsub_topic" "youtube_dlq" {
  name = "topic-youtube-dlq"
}
