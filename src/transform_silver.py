import json
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, to_timestamp, broadcast

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SilverTransformation")


def create_spark_session():
    return (
        SparkSession.builder
        .appName("DE_Capstone_Silver_Transform")
        .master("local[*]")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.parquet.compression.codec", "snappy")
        .getOrCreate()
    )


def load_category_mapping(spark, json_path):
    """Liest die US_category_id.json und baut ein Lookup-DataFrame (id -> category_name)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Unterstuetzt sowohl direkte Listen als auch YouTube API Root-Objekte mit 'items'
    items = data if isinstance(data, list) else data.get("items", [])

    categories = [
        {"category_id": str(item["id"]), "category_name": str(item["snippet"]["title"])}
        for item in items
    ]
    return spark.createDataFrame(categories)


def run_silver_transformation():
    # Pfade im Docker-Container (/app)
    bronze_path = "/app/data/bronze"
    raw_category_json = "/app/data/raw/US_category_id.json"
    silver_output = "/app/data/silver"

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    logger.info(f"Lese Bronze Parquet aus: {bronze_path}")
    df_bronze = spark.read.parquet(bronze_path)
    initial_count = df_bronze.count()
    logger.info(f"Gefundene Bronze-Datensätze: {initial_count}")

    # 1. Typisierung & Bereinigung
    # trending_date Format: '17.14.11' (yy.dd.MM)
    # publish_time Format: ISO 8601 (2017-11-13T17:13:01.000Z)
    df_cleaned = (
        df_bronze
        .withColumn("category_id", col("category_id").cast("string"))
        .withColumn("views", col("views").cast("long"))
        .withColumn("likes", col("likes").cast("long"))
        .withColumn("dislikes", col("dislikes").cast("long"))
        .withColumn("comment_count", col("comment_count").cast("long"))
        .withColumn("comments_disabled", col("comments_disabled").cast("boolean"))
        .withColumn("ratings_disabled", col("ratings_disabled").cast("boolean"))
        .withColumn("publish_time", to_timestamp(col("publish_time")))
        .withColumn("trending_date", to_date(col("trending_date"), "yy.dd.MM"))
    )

    # 2. Kategorie-Mapping per Broadcast Join (Zero Shuffle)
    logger.info("Lade Kategorie-Metadaten und führe Broadcast Join aus...")
    df_categories = load_category_mapping(spark, raw_category_json)

    df_silver = (
        df_cleaned.join(
            broadcast(df_categories),
            on="category_id",
            how="left"
        )
        .na.fill({"category_name": "Unknown"})
    )

    # 3. Speichern im Silver Layer (overwrite fuer idempotente Batch-Jobs)
    logger.info(f"Schreibe Silver Parquet nach: {silver_output}")
    (
        df_silver
        .write
        .mode("overwrite")
        .parquet(silver_output)
    )

    logger.info("=" * 60)
    logger.info(f"SILVER-TRANSFORMATION ERFOLGREICH! {initial_count} Datensätze verarbeitet.")
    logger.info("=" * 60)

    spark.stop()


if __name__ == "__main__":
    run_silver_transformation()
