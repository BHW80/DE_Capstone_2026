import logging
from pathlib import Path
from google.cloud import bigquery
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BigQueryLoader")

PROJECT_ID = "cloudanalytics-514018"
DATASET_ID = "youtube_analytics"
BUCKET_NAME = f"lakehouse-youtube-{PROJECT_ID}"
LOCATION = "EU"  # Europaeische Region (GCP Always Free Tier kompatibel)

ROOT_DIR = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT_DIR / "gcp_service_account.json"


def get_bigquery_client():
    if not KEY_PATH.exists():
        raise FileNotFoundError(
            f"Service Account Key nicht gefunden unter: {KEY_PATH}\n"
            f"Bitte lade den Key aus der GCP Console herunter und speichere ihn als 'gcp_service_account.json' im Projekt-Root!"
        )

    logger.info(f"Authentifiziere mit GCP Service Account Key: {KEY_PATH.name}...")
    credentials = service_account.Credentials.from_service_account_file(str(KEY_PATH))
    return bigquery.Client(credentials=credentials, project=PROJECT_ID)


def ensure_dataset(client):
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = LOCATION

    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset '{PROJECT_ID}.{DATASET_ID}' existiert bereits.")
    except Exception:
        logger.info(f"Erstelle neues BigQuery Dataset: '{PROJECT_ID}.{DATASET_ID}' (Location: {LOCATION})...")
        client.create_dataset(dataset, exists_ok=True)
        logger.info("Dataset erfolgreich erstellt!")


def load_silver_table_from_gcs(client):
    """Laedt die bereinigten Silver-Events direkt Cloud-to-Cloud aus dem GCS Lakehouse Bucket nach BigQuery."""
    gcs_uri = f"gs://{BUCKET_NAME}/silver/*.parquet"
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.silver_videos"

    logger.info(f"Starte Cloud-to-Cloud Load von '{gcs_uri}' in '{table_ref}'...")

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    load_job = client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    load_job.result()

    table = client.get_table(table_ref)
    logger.info(f"ERFOLG: Quelltabelle 'silver_videos' hat jetzt {table.num_rows} Zeilen in BigQuery (geladen aus GCS)!")


def run_cloud_load():
    logger.info("=" * 65)
    logger.info("STARTE GOOGLE BIGQUERY CLOUD-TO-CLOUD UPLOAD (GCS -> BIGQUERY)")
    logger.info("=" * 65)

    client = get_bigquery_client()
    ensure_dataset(client)
    load_silver_table_from_gcs(client)

    logger.info("=" * 65)
    logger.info("CLOUD-TO-CLOUD UPLOAD ERFOLGREICH ABGESCHLOSSEN!")
    logger.info(f"BigQuery Studio: https://console.cloud.google.com/bigquery?project={PROJECT_ID}")
    logger.info("=" * 65)


if __name__ == "__main__":
    run_cloud_load()
