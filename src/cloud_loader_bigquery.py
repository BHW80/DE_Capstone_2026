import logging
from pathlib import Path
from google.cloud import bigquery
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BigQueryLoader")

PROJECT_ID = "cloudanalytics-514018"
DATASET_ID = "youtube_analytics"
LOCATION = "EU"  # Europaeische Region (GCP Always Free Tier kompatibel)

ROOT_DIR = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT_DIR / "gcp_service_account.json"
DATA_GOLD_DIR = ROOT_DIR / "data" / "gold"


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


def load_parquet_table(client, table_name, folder_name):
    folder_path = DATA_GOLD_DIR / folder_name
    parquet_files = list(folder_path.glob("*.parquet"))

    if not parquet_files:
        logger.error(f"Keine Parquet-Dateien gefunden in: {folder_path}")
        return

    file_to_load = parquet_files[0]
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    logger.info(f"Lade '{file_to_load.name}' ({file_to_load.stat().st_size / 1024:.1f} KB) in BigQuery Tabelle '{table_ref}'...")

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Idempotentes Ueberschreiben
    )

    with open(file_to_load, "rb") as f:
        load_job = client.load_table_from_file(f, table_ref, job_config=job_config)

    load_job.result()  # Blockiert bis Upload & Schema-Erkennung in BigQuery fertig sind

    table = client.get_table(table_ref)
    logger.info(f"ERFOLG: Tabelle '{table_name}' hat jetzt {table.num_rows} Zeilen in BigQuery!")


def run_cloud_load():
    logger.info("=" * 60)
    logger.info(f"Starte BigQuery Cloud Ingestion fuer Projekt: {PROJECT_ID}")
    logger.info("=" * 60)

    client = get_bigquery_client()
    ensure_dataset(client)

    # Mart 1: Category KPIs
    load_parquet_table(client, "gold_category_kpis", "category_kpis")

    # Mart 2: Top-5 Trending Videos
    load_parquet_table(client, "gold_top_trending_videos", "top_trending_videos")

    logger.info("=" * 60)
    logger.info("CLOUD RELEASE ERFOLGREICH! Alle Gold-Marts sind jetzt in BigQuery online.")
    logger.info(f"Konsole oeffnen: https://console.cloud.google.com/bigquery?project={PROJECT_ID}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_cloud_load()
