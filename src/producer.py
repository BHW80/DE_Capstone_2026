import csv
import json
import logging
import random
import time
from pathlib import Path
from kafka import KafkaProducer

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("StreamingProducer")

# Konfiguration (127.0.0.1 fuer schnelles IPv4 ohne Disconnect-Lag)
BOOTSTRAP_SERVER = "127.0.0.1:9092"
TOPIC_INGEST = "topic_ingest"
TOPIC_ERR = "topic_err"
SAMPLE_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "sample" / "us_videos_mini_500.csv"
ERROR_RATE = 0.10  # 10% künstliche Fehler


def create_producer():
    logger.info(f"Verbinde zu Kafka Broker unter {BOOTSTRAP_SERVER}...")
    return KafkaProducer(
        bootstrap_servers=[BOOTSTRAP_SERVER],
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )


def run_producer():
    if not SAMPLE_CSV_PATH.exists():
        logger.error(f"Quelldatei nicht gefunden: {SAMPLE_CSV_PATH}")
        return

    producer = create_producer()
    logger.info(f"Starte Streaming von {SAMPLE_CSV_PATH.name}...")

    total_sent = 0
    clean_sent = 0
    err_sent = 0

    with open(SAMPLE_CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_sent += 1

            # Fault Injection: 10% Chance auf fehlerhaften Datensatz
            if random.random() < ERROR_RATE:
                # Absichtlicher Fehler: Views als ungültiger Text und Kennzeichnung
                corrupted_row = dict(row)
                corrupted_row["views"] = "CORRUPT_INVALID_NUMBER"
                corrupted_row["_error_reason"] = "Simulated fault injection: non-numeric views"

                producer.send(TOPIC_ERR, value=corrupted_row)
                err_sent += 1
                logger.warning(f"[{total_sent}] -> DLQ ({TOPIC_ERR}): Video '{row.get('title', '')[:30]}...'")
            else:
                producer.send(TOPIC_INGEST, value=row)
                clean_sent += 1
                if total_sent % 25 == 0:
                    logger.info(f"[{total_sent}] -> Ingest ({TOPIC_INGEST}): Video '{row.get('title', '')[:30]}...'")

            time.sleep(0.05)  # Kleine Pause fuer Live-Visualisierung

    # Sicherstellen, dass alle Puffer geleert sind
    producer.flush()
    producer.close()

    logger.info("=" * 50)
    logger.info(f"Streaming abgeschlossen! Gesamt: {total_sent} | Clean: {clean_sent} | DLQ/Fehler: {err_sent}")
    logger.info("=" * 50)


if __name__ == "__main__":
    run_producer()
