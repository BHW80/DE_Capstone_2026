import base64
import csv
import json
import logging
import random
from pathlib import Path
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CloudPubSubProducer")

PROJECT_ID = "cloudanalytics-514018"
TOPIC_INGEST = "topic-youtube-ingest"
TOPIC_DLQ = "topic-youtube-dlq"
ERROR_RATE = 0.10

ROOT_DIR = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT_DIR / "gcp_service_account.json"
SAMPLE_CSV = ROOT_DIR / "data" / "sample" / "us_videos_mini_500.csv"

# Deterministische SCD-2 Ziel-Video-ID & Mutationen (identisch zu v2.0 producer.py)
SCD2_TARGET_VIDEO_ID = "2kyS6SvSYSE"
SCD2_MUTATIONS = {
    2: {
        "title": "WE WANT TO TALK ABOUT OUR MARRIAGE (Official Update)",
        "tags": "marriage|relationship|update|vlog"
    },
    3: {
        "title": "WE WANT TO TALK ABOUT OUR MARRIAGE [THE TRUTH]",
        "tags": "marriage|relationship|update|vlog|truth"
    }
}


def get_session():
    if not KEY_PATH.exists():
        raise FileNotFoundError(f"GCP Service Account Key fehlt unter: {KEY_PATH}")
    credentials = service_account.Credentials.from_service_account_file(
        str(KEY_PATH),
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return AuthorizedSession(credentials)


def publish_batch(session, topic_name, messages):
    """Sendet eine Liste von Nachrichten per Google Cloud Pub/Sub REST API."""
    if not messages:
        return 0
    url = f"https://pubsub.googleapis.com/v1/projects/{PROJECT_ID}/topics/{topic_name}:publish"
    resp = session.post(url, json={"messages": messages})
    if resp.status_code != 200:
        raise RuntimeError(f"Pub/Sub Publish Fehler auf {topic_name}: {resp.status_code} - {resp.text}")
    msg_ids = resp.json().get("messageIds", [])
    return len(msg_ids)


def run_pubsub_producer():
    if not SAMPLE_CSV.exists():
        logger.error(f"Sample CSV nicht gefunden: {SAMPLE_CSV}")
        return

    logger.info(f"Authentifiziere gegen Google Cloud Pub/Sub (Projekt: {PROJECT_ID})...")
    session = get_session()

    ingest_batch = []
    dlq_batch = []
    scd2_occurrence_count = 0

    with open(SAMPLE_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vid = row["video_id"]

            # 1. Deterministische SCD-2 Mutation fuer unser Ziel-Video
            if vid == SCD2_TARGET_VIDEO_ID:
                scd2_occurrence_count += 1
                if scd2_occurrence_count in SCD2_MUTATIONS:
                    old_title = row["title"]
                    row.update(SCD2_MUTATIONS[scd2_occurrence_count])
                    logger.info(
                        f"[SCD-2 MUTATION #{scd2_occurrence_count}] Video '{vid}' "
                        f"(Tag {row['trending_date']}): '{old_title}' -> '{row['title']}'"
                    )

            # 2. Fault Injection (10% korrupte Daten -> Cloud Pub/Sub DLQ Topic)
            if vid != SCD2_TARGET_VIDEO_ID and random.random() < ERROR_RATE:
                corrupted_row = dict(row)
                corrupted_row["views"] = "CORRUPT_INVALID_NUMBER"
                corrupted_row["_error_reason"] = "Simulated fault injection: non-numeric views"
                b64_data = base64.b64encode(json.dumps(corrupted_row).encode("utf-8")).decode("ascii")
                dlq_batch.append({"data": b64_data, "attributes": {"video_id": vid, "stream": "dlq"}})
            else:
                b64_data = base64.b64encode(json.dumps(row).encode("utf-8")).decode("ascii")
                ingest_batch.append({"data": b64_data, "attributes": {"video_id": vid, "stream": "clean"}})

    logger.info(f"Publiziere {len(ingest_batch)} valide Events nach '{TOPIC_INGEST}'...")
    sent_clean = publish_batch(session, TOPIC_INGEST, ingest_batch)

    logger.info(f"Publiziere {len(dlq_batch)} korrupte Events nach '{TOPIC_DLQ}'...")
    sent_dlq = publish_batch(session, TOPIC_DLQ, dlq_batch)

    logger.info("=" * 60)
    logger.info("SERVERLESS CLOUD PUB/SUB STREAMING BEENDET:")
    logger.info(f"-> Clean Events ('{TOPIC_INGEST}'): {sent_clean}")
    logger.info(f"-> DLQ Events   ('{TOPIC_DLQ}'):    {sent_dlq}")
    logger.info(f"-> SCD-2 Events fuer '{SCD2_TARGET_VIDEO_ID}': {scd2_occurrence_count} Versionen")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pubsub_producer()
