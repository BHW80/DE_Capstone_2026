import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CloudPubSubDLQConsumer")

PROJECT_ID = "cloudanalytics-514018"
SUBSCRIPTION_DLQ = "sub-youtube-dlq"

ROOT_DIR = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT_DIR / "gcp_service_account.json"
QUARANTINE_DIR = ROOT_DIR / "data" / "quarantine"


def get_session():
    credentials = service_account.Credentials.from_service_account_file(
        str(KEY_PATH),
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return AuthorizedSession(credentials)


def run_pubsub_dlq_consumer():
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    session = get_session()

    pull_url = f"https://pubsub.googleapis.com/v1/projects/{PROJECT_ID}/subscriptions/{SUBSCRIPTION_DLQ}:pull"
    ack_url = f"https://pubsub.googleapis.com/v1/projects/{PROJECT_ID}/subscriptions/{SUBSCRIPTION_DLQ}:acknowledge"

    logger.info(f"Ziehe Quarantaene-Nachrichten aus Cloud Pub/Sub Subscription '{SUBSCRIPTION_DLQ}'...")
    records = []

    while True:
        resp = session.post(pull_url, json={"returnImmediately": True, "maxMessages": 500})
        if resp.status_code != 200:
            raise RuntimeError(f"Pub/Sub DLQ Pull Fehler: {resp.status_code} - {resp.text}")

        received = resp.json().get("receivedMessages", [])
        if not received:
            break

        ack_ids = []
        for idx, item in enumerate(received):
            ack_ids.append(item["ackId"])
            msg = item["message"]
            raw_json = base64.b64decode(msg["data"]).decode("utf-8")
            record = json.loads(raw_json)

            # Quarantaene Audit-Metadaten
            record["_quarantine_at"] = datetime.now(timezone.utc).isoformat()
            record["_kafka_offset"] = len(records) + idx
            record["_kafka_partition"] = 0
            records.append(record)

        session.post(ack_url, json={"ackIds": ack_ids})
        logger.info(f"{len(received)} DLQ-Nachrichten empfangen und bestaetigt (Gesamt: {len(records)})...")

    if not records:
        logger.warning(f"Keine Nachrichten in '{SUBSCRIPTION_DLQ}' gefunden.")
        return

    df = pd.DataFrame(records)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = QUARANTINE_DIR / f"quarantine_videos_{timestamp_str}.parquet"
    df.to_parquet(output_file, engine="pyarrow", index=False)

    logger.info("=" * 60)
    logger.info(f"DLQ-ERFOLG (CLOUD PUB/SUB -> QUARANTINE): {len(df)} fehlerhafte Datensaetze isoliert:")
    logger.info(f"-> Speicherort: {output_file.relative_to(ROOT_DIR)}")
    logger.info(f"-> Dateigroesse: {output_file.stat().st_size / 1024:.1f} KB")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pubsub_dlq_consumer()
