import json
import logging
import time
from pathlib import Path
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WorkflowRunner")

PROJECT_ID = "cloudanalytics-514018"
REGION = "europe-west3"
WORKFLOW_NAME = "youtube-dataops-pipeline"
KEY_PATH = Path(__file__).resolve().parent.parent / "gcp_service_account.json"


def run_workflow():
    if not KEY_PATH.exists():
        logger.error(f"GCP Key nicht gefunden unter: {KEY_PATH}")
        return

    logger.info(f"Authentifiziere mit GCP Service Account: {KEY_PATH.name}...")
    credentials = service_account.Credentials.from_service_account_file(
        str(KEY_PATH),
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)

    trigger_url = (
        f"https://workflowexecutions.googleapis.com/v1/projects/{PROJECT_ID}/"
        f"locations/{REGION}/workflows/{WORKFLOW_NAME}/executions"
    )

    logger.info(f"Starte Ausfuehrung von Cloud Workflow '{WORKFLOW_NAME}'...")
    response = session.post(trigger_url, json={})

    if response.status_code != 200:
        logger.error(f"Fehler beim Starten: {response.status_code} - {response.text}")
        return

    execution = response.json()
    execution_id = execution.get("name")
    short_id = execution_id.split("/")[-1] if execution_id else "unknown"
    logger.info(f"Workflow erfolgreich gestartet! Execution ID: {short_id}")

    # Polling bis zum Abschluss
    status_url = f"https://workflowexecutions.googleapis.com/v1/{execution_id}"
    while True:
        time.sleep(3)
        poll_resp = session.get(status_url).json()
        state = poll_resp.get("state")
        logger.info(f"Aktueller Workflow-Status: {state}...")

        if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            logger.info("=" * 60)
            if state == "SUCCEEDED":
                logger.info("ERFOLG: Cloud Workflow erfolgreich abgeschlossen!")
                logger.info(f"Ergebnis: {poll_resp.get('result', '{}')}")
            else:
                logger.error(f"FEHLER: Workflow beendet mit Status '{state}'")
                logger.error(f"Details: {poll_resp.get('error', '{}')}")
            logger.info("=" * 60)
            break


if __name__ == "__main__":
    run_workflow()
