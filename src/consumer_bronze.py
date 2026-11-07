import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from kafka import KafkaConsumer

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("BronzeConsumer")

# Konfiguration (127.0.0.1 fuer schnelles IPv4 ohne Disconnect-Lag)
BOOTSTRAP_SERVER = "127.0.0.1:9092"
TOPIC_INGEST = "topic_ingest"
CONSUMER_GROUP = "bronze_consumer_group"
BRONZE_DIR = Path(__file__).resolve().parent.parent / "data" / "bronze"


def run_consumer():
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Verbinde zu Kafka ({BOOTSTRAP_SERVER}), Gruppe '{CONSUMER_GROUP}'...")
    logger.info(f"Abonniere Topic '{TOPIC_INGEST}'...")

    consumer = KafkaConsumer(
        TOPIC_INGEST,
        bootstrap_servers=[BOOTSTRAP_SERVER],
        group_id=CONSUMER_GROUP,
        auto_offset_reset="earliest",  # Liest ab Offset 0, falls noch keine Offsets committet wurden
        enable_auto_commit=True,
        consumer_timeout_ms=5000,      # Stoppt nach 5s Inaktivitaet (Batch Ingestion)
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))
    )

    records = []
    logger.info("Warte auf Nachrichten (Timeout nach 5s Inaktivitaet)...")

    for message in consumer:
        record = message.value

        # Bronze Audit-Metadaten hinzufuegen
        record["_ingested_at"] = datetime.now(timezone.utc).isoformat()
        record["_kafka_offset"] = message.offset
        record["_kafka_partition"] = message.partition

        records.append(record)

        if len(records) % 50 == 0:
            logger.info(f"{len(records)} Nachrichten empfangen...")

    consumer.close()

    if not records:
        logger.warning("Keine neuen Nachrichten in 'topic_ingest' gefunden.")
        return

    # In DataFrame konvertieren und als Parquet speichern
    df = pd.DataFrame(records)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = BRONZE_DIR / f"bronze_videos_{timestamp_str}.parquet"

    df.to_parquet(output_file, engine="pyarrow", index=False)

    logger.info("=" * 60)
    logger.info(f"ERFOLG: {len(df)} Zeilen in Bronze Parquet geschrieben:")
    logger.info(f"-> Speicherort: {output_file.relative_to(BRONZE_DIR.parent.parent)}")
    logger.info(f"-> Dateigroesse: {output_file.stat().st_size / 1024:.1f} KB")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_consumer()
