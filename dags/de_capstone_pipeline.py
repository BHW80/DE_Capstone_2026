import logging
from datetime import datetime
from pathlib import Path
import docker
from airflow.decorators import dag, task

HOST_PROJECT_DIR = "d:/Projekte/CloudEng/DE_Capstone_2026"
AIRFLOW_DATA_DIR = Path("/opt/airflow/data")
logger = logging.getLogger("airflow.task")


def run_spark_container(script_name: str):
    """Startet den fluechtigen Spark-Container ueber den gemounteten Docker-Socket."""
    client = docker.from_env()
    logger.info(f"Spawne de_spark Container fuer {script_name}...")

    logs = client.containers.run(
        image="apache/spark-py:latest",
        command=f"/opt/spark/bin/spark-submit /app/src/{script_name}",
        volumes={HOST_PROJECT_DIR: {"bind": "/app", "mode": "rw"}},
        user="root",
        remove=True,  # Container nach Abschluss automatisch zerstoeren
        stdout=True,
        stderr=True
    )
    return logs.decode("utf-8", errors="replace")


@dag(
    dag_id="de_capstone_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,  # Manueller Start im Web-UI fuer Tests
    catchup=False,
    tags=["medallion", "spark", "youtube", "capstone"]
)
def medallion_pipeline():

    @task
    def check_bronze_landing() -> int:
        """Prueft, ob Rohdaten in Bronze vorhanden sind."""
        bronze_files = list((AIRFLOW_DATA_DIR / "bronze").glob("*.parquet"))
        if not bronze_files:
            raise FileNotFoundError("Keine Bronze-Parquet-Dateien auf der Laderampe gefunden!")
        logger.info(f"Gate 1 bestanden: {len(bronze_files)} Bronze-Datei(en) bereit.")
        return len(bronze_files)

    @task
    def trigger_spark_silver(bronze_file_count: int):
        """Fuehrt den Silver Cleaning & Broadcast Join Job aus."""
        logger.info(f"Starte Silver-Job fuer {bronze_file_count} Bronze-Dateien...")
        spark_log = run_spark_container("transform_silver.py")
        logger.info("Spark Silver Output:\n" + spark_log[-600:])
        return "Silver abgeschlossen"

    @task
    def trigger_spark_gold(silver_status: str):
        """Fuehrt den Gold Aggregations & Window Functions Job aus."""
        logger.info("Starte Gold-Job (Category KPIs & Top-5 Rankings)...")
        spark_log = run_spark_container("transform_gold.py")
        logger.info("Spark Gold Output:\n" + spark_log[-600:])
        return "Gold abgeschlossen"

    @task
    def validate_gold_quality(gold_status: str):
        """Data Quality Gate: Prueft, ob beide Gold-Marts existieren und Daten enthalten."""
        kpi_files = list((AIRFLOW_DATA_DIR / "gold" / "category_kpis").glob("*.parquet"))
        top_files = list((AIRFLOW_DATA_DIR / "gold" / "top_trending_videos").glob("*.parquet"))

        if not kpi_files or not top_files:
            raise RuntimeError("Data Quality Check fehlgeschlagen: Mindestens ein Gold-Mart fehlt!")

        logger.info("=" * 60)
        logger.info("DATA QUALITY GATE: BESTANDEN (100% OK)")
        logger.info(f"-> Category KPIs Parquet: {kpi_files[0].name}")
        logger.info(f"-> Top-Trending Parquet: {top_files[0].name}")
        logger.info("Pipeline erfolgreich durchlaufen!")
        logger.info("=" * 60)

    # Pipeline-Abhaengigkeiten (Workflow-Graph)
    bronze_ok = check_bronze_landing()
    silver_ok = trigger_spark_silver(bronze_ok)
    gold_ok = trigger_spark_gold(silver_ok)
    validate_gold_quality(gold_ok)


pipeline = medallion_pipeline()
