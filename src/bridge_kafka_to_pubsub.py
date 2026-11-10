import base64
import json
import logging
import time
from pathlib import Path
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from kafka import KafkaConsumer

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("HybridKafkaToPubSubBridge")

# Konfiguration
BOOTSTRAP_SERVER = "127.0.0.1:9092"
KAFKA_TOPIC_INGEST = "topic_ingest"
KAFKA_TOPIC_ERR = "topic_err"
CONSUMER_GROUP = "hybrid_bridge_consumer_group"

PROJECT_ID = "cloudanalytics-514018"
PUBSUB_TOPIC_INGEST = "topic-youtube-ingest"
PUBSUB_TOPIC_DLQ = "topic-youtube-dlq"

ROOT_DIR = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT_DIR / "gcp_service_account.json"
BATCH_SIZE = 100


def get_gcp_session():
    """Authentifiziert sich bei der Google Cloud Platform ueber den Service Account Key."""
    if not KEY_PATH.exists():
        raise FileNotFoundError(f"GCP Service Account Key nicht gefunden: {KEY_PATH}")
    credentials = service_account.Credentials.from_service_account_file(
        str(KEY_PATH),
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return AuthorizedSession(credentials)


def publish_pubsub_batch(session, pubsub_topic, records):
    """Verschickt eine Liste von Records als Batch per HTTPS REST API an Cloud Pub/Sub."""
    if not records:
        return 0

    url = f"https://pubsub.googleapis.com/v1/projects/{PROJECT_ID}/topics/{pubsub_topic}:publish"
    pubsub_messages = []
    for r in records:
        payload = json.dumps(r).encode("utf-8")
        pubsub_messages.append({
            "data": base64.b64encode(payload).decode("utf-8"),
            "attributes": {
                "source": "hybrid_onprem_kafka_bridge",
                "bridged_at": str(time.time())
            }
        })

    resp = session.post(url, json={"messages": pubsub_messages})
    if resp.status_code != 200:
        logger.error(f"Fehler beim Pub/Sub Batch Publish auf {pubsub_topic}: {resp.status_code} - {resp.text}")
        raise RuntimeError(f"Pub/Sub API Fehler: {resp.status_code}")

    message_ids = resp.json().get("messageIds", [])
    return len(message_ids)


def run_bridge():
    logger.info("=" * 65)
    logger.info("Starte Hybrid Bridge: On-Premises Kafka -> Google Cloud Pub/Sub")
    logger.info(f"Kafka:   {BOOTSTRAP_SERVER} (Topics: {KAFKA_TOPIC_INGEST}, {KAFKA_TOPIC_ERR})")
    logger.info(f"Pub/Sub: {PROJECT_ID} (Topics: {PUBSUB_TOPIC_INGEST}, {PUBSUB_TOPIC_DLQ})")
    logger.info("=" * 65)

    session = get_gcp_session()
    logger.info("GCP OAuth2-Session erfolgreich initialisiert.")

    logger.info(f"Verbinde zu Kafka Broker ({BOOTSTRAP_SERVER}), Consumer-Gruppe '{CONSUMER_GROUP}'...")
    consumer = KafkaConsumer(
        KAFKA_TOPIC_INGEST,
        KAFKA_TOPIC_ERR,
        bootstrap_servers=[BOOTSTRAP_SERVER],
        group_id=CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        consumer_timeout_ms=5000,  # Wartet bis zu 5s auf neue Events
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))
    )

    ingest_buffer = []
    dlq_buffer = []
    total_ingest_bridged = 0
    total_dlq_bridged = 0

    logger.info("Lausche auf Kafka-Events (Timeout nach 5s Inaktivitaet)...")

    for message in consumer:
        val = message.value
        topic = message.topic

        if topic == KAFKA_TOPIC_INGEST:
            ingest_buffer.append(val)
            if len(ingest_buffer) >= BATCH_SIZE:
                sent = publish_pubsub_batch(session, PUBSUB_TOPIC_INGEST, ingest_buffer)
                total_ingest_bridged += sent
                logger.info(f"-> Batch von {sent} Ingest-Events an Cloud Pub/Sub '{PUBSUB_TOPIC_INGEST}' gestreamt.")
                ingest_buffer.clear()
        elif topic == KAFKA_TOPIC_ERR:
            dlq_buffer.append(val)
            if len(dlq_buffer) >= BATCH_SIZE:
                sent = publish_pubsub_batch(session, PUBSUB_TOPIC_DLQ, dlq_buffer)
                total_dlq_bridged += sent
                logger.info(f"-> Batch von {sent} DLQ-Events an Cloud Pub/Sub '{PUBSUB_TOPIC_DLQ}' gestreamt.")
                dlq_buffer.clear()

    # Flush verbleibender Puffer
    if ingest_buffer:
        sent = publish_pubsub_batch(session, PUBSUB_TOPIC_INGEST, ingest_buffer)
        total_ingest_bridged += sent
        logger.info(f"-> Finaler Flush: {sent} Ingest-Events an Cloud Pub/Sub '{PUBSUB_TOPIC_INGEST}' gestreamt.")

    if dlq_buffer:
        sent = publish_pubsub_batch(session, PUBSUB_TOPIC_DLQ, dlq_buffer)
        total_dlq_bridged += sent
        logger.info(f"-> Finaler Flush: {sent} DLQ-Events an Cloud Pub/Sub '{PUBSUB_TOPIC_DLQ}' gestreamt.")

    logger.info("=" * 65)
    logger.info("Hybrid Bridge Zusammenfassung:")
    logger.info(f"  * Saubere Ingest-Events gestreamt: {total_ingest_bridged}")
    logger.info(f"  * Fehlerhafte DLQ-Events gestreamt: {total_dlq_bridged}")
    logger.info(f"  * Gesamtanzahl uebertragen:        {total_ingest_bridged + total_dlq_bridged}")
    logger.info("=" * 65)


if __name__ == "__main__":
    run_bridge()
