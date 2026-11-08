import base64
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import pandas as pd
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CloudPubSubDLQConsumer")

PROJECT_ID = "cloudanalytics-514018"
BUCKET_NAME = f"lakehouse-youtube-{PROJECT_ID}"
SUBSCRIPTION_DLQ = "sub-youtube-dlq"

ROOT_DIR = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT_DIR / "gcp_service_account.json"


def get_session():
    credentials = service_account.Credentials.from_service_account_file(
        str(KEY_PATH),
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return AuthorizedSession(credentials)


def delete_existing_gcs_prefix(session: AuthorizedSession, prefix: str):
    list_url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET_NAME}/o"
    resp = session.get(list_url, params={"prefix": prefix})
    if resp.status_code == 200:
        for item in resp.json().get("items", []):
            obj_name = item["name"]
            del_url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET_NAME}/o/{quote(obj_name, safe='')}"
            session.delete(del_url)


def upload_bytes_to_gcs(session: AuthorizedSession, object_name: str, data_bytes: bytes):
    upload_url = f"https://storage.googleapis.com/upload/storage/v1/b/{BUCKET_NAME}/o"
    resp = session.post(
        upload_url,
        params={"uploadType": "media", "name": object_name},
        data=data_bytes,
        headers={"Content-Type": "application/octet-stream"}
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"GCS Upload Fehler ({object_name}): {resp.status_code} - {resp.text}")


def run_pubsub_dlq_consumer():
    session = get_session()

    pull_url = f"https://pubsub.googleapis.com/v1/projects/{PROJECT_ID}/subscriptions/{SUBSCRIPTION_DLQ}:pull"
    ack_url = f"https://pubsub.googleapis.com/v1/projects/{PROJECT_ID}/subscriptions/{SUBSCRIPTION_DLQ}:acknowledge"

    logger.info(f"Pruefe Dead Letter Queue Subscription '{SUBSCRIPTION_DLQ}' auf fehlerhafte Events...")
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

            # DLQ Quarantaene Audit-Metadaten
            record["_quarantine_at"] = datetime.now(timezone.utc).isoformat()
            record["_dlq_offset"] = len(records) + idx
            record["_dlq_partition"] = 0
            records.append(record)

        session.post(ack_url, json={"ackIds": ack_ids})
        logger.info(f"{len(received)} DLQ-Nachrichten empfangen und bestaetigt (Gesamt: {len(records)})...")

    if not records:
        logger.info(f"Keine fehlerhaften Nachrichten in '{SUBSCRIPTION_DLQ}' gefunden.")
        return

    df = pd.DataFrame(records)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    gcs_object_name = f"quarantine/quarantine_videos_{timestamp_str}.parquet"

    # In-Memory Parquet erzeugen (0 lokale Dateien!) und direkt in den GCS Lakehouse Bucket schreiben
    buf = io.BytesIO()
    df.to_parquet(buf, engine="pyarrow", index=False)
    parquet_bytes = buf.getvalue()

    delete_existing_gcs_prefix(session, "quarantine/")
    upload_bytes_to_gcs(session, gcs_object_name, parquet_bytes)

    logger.info("=" * 65)
    logger.info(f"QUARANTAENE-ISOLATION (CLOUD PUB/SUB -> GCS DLQ): {len(df)} korrupte Zeilen isoliert!")
    logger.info(f"-> GCS URI: gs://{BUCKET_NAME}/{gcs_object_name}")
    logger.info(f"-> Dateigroesse: {len(parquet_bytes) / 1024:.1f} KB (0 lokale Parquet-Dateien)")
    logger.info("=" * 65)


if __name__ == "__main__":
    run_pubsub_dlq_consumer()
