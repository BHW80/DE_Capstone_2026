variable "project_id" {
  description = "Die Google Cloud Projekt-ID"
  type        = string
  default     = "cloudanalytics-514018"
}

variable "region" {
  description = "GCP Region (Europäischer Standort)"
  type        = string
  default     = "europe-west3" # Frankfurt
}

variable "location" {
  description = "Multi-Region Standort für BigQuery und GCS"
  type        = string
  default     = "EU"
}

variable "credentials_file" {
  description = "Pfad zum GCP Service Account Key"
  type        = string
  default     = "../gcp_service_account.json"
}

variable "service_account_email" {
  description = "E-Mail des ausführenden GCP Service Accounts"
  type        = string
  default     = "cloudanalytics-514018@cloudanalytics-514018.iam.gserviceaccount.com"
}
