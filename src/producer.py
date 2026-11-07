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

# SCD-2 Simulations-Konfiguration (Demonstriert Metadaten-Evolution im Stream)
SCD2_TARGET_VIDEO_ID = "2kyS6SvSYSE"
SCD2_MUTATIONS = {
    2: {
        "title": "WE WANT TO TALK ABOUT OUR MARRIAGE (Official Update)",
        "tags": "marriage|relationship|update|vlog",
    },
    3: {
        "title": "WE WANT TO TALK ABOUT OUR MARRIAGE [THE TRUTH]",
        "tags": "marriage|relationship|update|vlog|truth",
    },
}


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
    scd2_events_count = 0
    video_occurrences = {}

    with open(SAMPLE_CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_sent += 1
            vid = row.get("video_id", "")
            video_occurrences[vid] = video_occurrences.get(vid, 0) + 1
            occ = video_occurrences[vid]

            # SCD-2 Mutation: Metadaten-Änderung für das Ziel-Video bei späteren Auftritten
            if vid == SCD2_TARGET_VIDEO_ID and occ in SCD2_MUTATIONS:
                mutation = SCD2_MUTATIONS[occ]
                row["title"] = mutation["title"]
                row["tags"] = mutation["tags"]
                scd2_events_count += 1
                logger.info(
                    f"[{total_sent}] 🔄 SCD-2 EVENT INJECTED: Video '{vid}' (Occurrence #{occ}) "
                    f"-> New Title: '{row['title']}'"
                )

            # Fault Injection: 10% Chance auf fehlerhaften Datensatz (ausgenommen das SCD-2 Demovideo)
            if vid != SCD2_TARGET_VIDEO_ID and random.random() < ERROR_RATE:
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

    logger.info("=" * 60)
    logger.info(
        f"Streaming abgeschlossen! Gesamt: {total_sent} | Clean: {clean_sent} "
        f"| DLQ/Fehler: {err_sent} | SCD-2 Mutationen: {scd2_events_count}"
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    run_producer()
