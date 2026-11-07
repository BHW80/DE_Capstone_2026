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
logger = logging.getLogger("DLQConsumer")

# Konfiguration (127.0.0.1 fuer schnelles IPv4 ohne Disconnect-Lag)
BOOTSTRAP_SERVER = "127.0.0.1:9092"
TOPIC_ERR = "topic_err"
CONSUMER_GROUP = "dlq_consumer_group"
QUARANTINE_DIR = Path(__file__).resolve().parent.parent / "data" / "quarantine"


def run_dlq_consumer():
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Verbinde zu Kafka ({BOOTSTRAP_SERVER}), Gruppe '{CONSUMER_GROUP}'...")
    logger.info(f"Abonniere Dead Letter Queue Topic '{TOPIC_ERR}'...")

    consumer = KafkaConsumer(
        TOPIC_ERR,
        bootstrap_servers=[BOOTSTRAP_SERVER],
        group_id=CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        consumer_timeout_ms=5000,
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))
    )

    records = []
    logger.info("Lese Quarantäne-Nachrichten (Timeout nach 5s Inaktivitaet)...")

    for message in consumer:
        record = message.value

        # Quarantäne Audit-Metadaten
        record["_quarantine_at"] = datetime.now(timezone.utc).isoformat()
        record["_kafka_offset"] = message.offset
        record["_kafka_partition"] = message.partition

        records.append(record)

    consumer.close()

    if not records:
        logger.warning(f"Keine Nachrichten in '{TOPIC_ERR}' gefunden.")
        return

    # In DataFrame konvertieren und als Parquet wegschreiben
    df = pd.DataFrame(records)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = QUARANTINE_DIR / f"quarantine_videos_{timestamp_str}.parquet"

    df.to_parquet(output_file, engine="pyarrow", index=False)

    logger.info("=" * 60)
    logger.info(f"DLQ-ERFOLG: {len(df)} fehlerhafte Datensätze isoliert:")
    logger.info(f"-> Speicherort: {output_file.relative_to(QUARANTINE_DIR.parent.parent)}")
    logger.info(f"-> Dateigroesse: {output_file.stat().st_size / 1024:.1f} KB")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_dlq_consumer()
