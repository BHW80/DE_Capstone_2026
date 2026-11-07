import logging
from datetime import datetime
from pathlib import Path
from google.cloud import bigquery
from google.oauth2 import service_account
from airflow.decorators import dag, task

PROJECT_ID = "cloudanalytics-514018"
DATASET_ID = "youtube_analytics"
LOCATION = "EU"

AIRFLOW_DATA_DIR = Path("/opt/airflow/data")
KEY_PATH = Path("/app/gcp_service_account.json")
logger = logging.getLogger("airflow.task")


@dag(
    dag_id="de_cloud_release_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,  # Manueller Start fuer gezielte Cloud-Releases
    catchup=False,
    tags=["cloud", "bigquery", "release", "capstone"]
)
def cloud_release_pipeline():

    @task
    def check_gold_data_ready() -> dict:
        """Prueft, ob beide Gold-Marts bereitstehen."""
        kpi_files = list((AIRFLOW_DATA_DIR / "gold" / "category_kpis").glob("*.parquet"))
        top_files = list((AIRFLOW_DATA_DIR / "gold" / "top_trending_videos").glob("*.parquet"))

        if not kpi_files or not top_files:
            raise FileNotFoundError("Keine Gold-Marts gefunden! Bitte zuerst DAG 'de_capstone_pipeline' ausfuehren.")

        logger.info(f"Gold-Marts bereit: {kpi_files[0].name} und {top_files[0].name}")
        return {
            "kpi_path": str(kpi_files[0]),
            "top_path": str(top_files[0])
        }

    @task
    def sync_to_bigquery(gold_files: dict):
        """Laedt die Parquet-Marts nach Google BigQuery hoch."""
        if not KEY_PATH.exists():
            raise FileNotFoundError(f"GCP Key nicht gefunden unter {KEY_PATH}")

        credentials = service_account.Credentials.from_service_account_file(str(KEY_PATH))
        client = bigquery.Client(credentials=credentials, project=PROJECT_ID)

        # Dataset sicherstellen
        dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = LOCATION
        client.create_dataset(dataset, exists_ok=True)

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        # Mart 1 hochladen
        kpi_path = Path(gold_files["kpi_path"])
        with open(kpi_path, "rb") as f:
            load_kpi = client.load_table_from_file(
                f, f"{PROJECT_ID}.{DATASET_ID}.gold_category_kpis", job_config=job_config
            )
        load_kpi.result()

        # Mart 2 hochladen
        top_path = Path(gold_files["top_path"])
        with open(top_path, "rb") as f:
            load_top = client.load_table_from_file(
                f, f"{PROJECT_ID}.{DATASET_ID}.gold_top_trending_videos", job_config=job_config
            )
        load_top.result()

        logger.info("=" * 60)
        logger.info("BIGQUERY SYNC ERFOLGREICH!")
        logger.info(f"Projekt: {PROJECT_ID} | Dataset: {DATASET_ID}")
        logger.info("Looker Studio Dashboard ist jetzt auf dem neuesten Stand.")
        logger.info("=" * 60)

    gold_info = check_gold_data_ready()
    sync_to_bigquery(gold_info)


pipeline = cloud_release_pipeline()
