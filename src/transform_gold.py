import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum, round, dense_rank
from pyspark.sql.window import Window

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GoldTransformation")


def create_spark_session():
    return (
        SparkSession.builder
        .appName("DE_Capstone_Gold_Transform")
        .master("local[*]")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.parquet.compression.codec", "snappy")
        .getOrCreate()
    )


def run_gold_transformation():
    silver_path = "/app/data/silver"
    gold_kpi_output = "/app/data/gold/category_kpis"
    gold_top_output = "/app/data/gold/top_trending_videos"

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    logger.info(f"Lese bereinigten Silver-Layer aus: {silver_path}")
    df_silver = spark.read.parquet(silver_path)

    # -------------------------------------------------------------
    # Mart 1: Category KPIs & Engagement Rate
    # -------------------------------------------------------------
    logger.info("Erstelle Mart 1: Category KPIs...")
    df_category_kpis = (
        df_silver
        .groupBy("category_name")
        .agg(
            count("video_id").alias("total_videos"),
            sum("views").alias("total_views"),
            sum("likes").alias("total_likes"),
            sum("comment_count").alias("total_comments"),
            round((sum(col("likes") + col("comment_count")) / sum("views")) * 100, 2).alias("avg_engagement_rate_pct")
        )
        .orderBy(col("total_views").desc())
    )

    # -------------------------------------------------------------
    # Mart 2: Top-5 Trending Videos je Kategorie (Window Function)
    # -------------------------------------------------------------
    logger.info("Erstelle Mart 2: Top-5 Rankings mit Window Functions...")
    window_spec = Window.partitionBy("category_name").orderBy(col("views").desc())

    df_top_trending = (
        df_silver
        .withColumn("rank_in_category", dense_rank().over(window_spec))
        .filter(col("rank_in_category") <= 5)
        .select(
            "category_name",
            "rank_in_category",
            "title",
            "channel_title",
            "views",
            "likes",
            "comment_count",
            "publish_time"
        )
        .orderBy("category_name", "rank_in_category")
    )

    # -------------------------------------------------------------
    # Speichern nach /app/data/gold (mit coalesce(1) gegen Small-Files)
    # -------------------------------------------------------------
    logger.info(f"Schreibe Mart 1 nach: {gold_kpi_output}")
    df_category_kpis.coalesce(1).write.mode("overwrite").parquet(gold_kpi_output)

    logger.info(f"Schreibe Mart 2 nach: {gold_top_output}")
    df_top_trending.coalesce(1).write.mode("overwrite").parquet(gold_top_output)

    logger.info("=" * 60)
    logger.info("GOLD-TRANSFORMATION ERFOLGREICH ABGESCHLOSSEN!")
    logger.info("=" * 60)

    spark.stop()


if __name__ == "__main__":
    run_gold_transformation()
