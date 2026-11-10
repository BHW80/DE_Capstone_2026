import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("CRM_API_Extractor")

# Konfiguration
API_URL = "https://www.weltler.at/api/get_contracts.php"
API_TOKEN = "de_capstone_2026_secret_token"

PROJECT_ID = "cloudanalytics-514018"
GCS_BUCKET = f"lakehouse-youtube-{PROJECT_ID}"
GCS_DEST_BLOB = "bronze/crm_contracts/creator_contracts.parquet"

ROOT_DIR = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT_DIR / "gcp_service_account.json"


def get_gcs_session():
    """Erstellt eine authentifizierte OAuth2-Session fuer Google Cloud Storage."""
    if not KEY_PATH.exists():
        raise FileNotFoundError(f"GCP Service Account Key nicht gefunden: {KEY_PATH}")
    credentials = service_account.Credentials.from_service_account_file(
        str(KEY_PATH),
        scopes=["https://www.googleapis.com/auth/devstorage.read_write"]
    )
    return AuthorizedSession(credentials)


def fetch_contracts_from_api():
    """Ruft die Creator-Vertraege von der gesicherten REST-API auf www.weltler.at ab."""
    logger.info(f"Frage CRM REST-API ab: {API_URL} ...")
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "User-Agent": "DE_Capstone_DataOps_Platform/2026"
    }

    try:
        response = requests.get(API_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            records = data.get("data", [])
            logger.info(f"Erfolgreich {len(records)} Vertraege live von MariaDB ({data.get('source')}) abgerufen.")
            return records
        else:
            logger.warning(f"API antwortete mit Status {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Konnte {API_URL} nicht erreichen ({e}).")

    logger.info("Nutze lokalen Fallback (Seeds), bis die PHP-Datei auf www.weltler.at hinterlegt ist.")
    return get_fallback_seeds()


def get_fallback_seeds():
    """Liefert synthetische Fallback-Seeds, falls der Webserver noch nicht live konfiguriert ist."""
    return [
        {"contract_id": 1, "channel_title": "CaseyNeistat", "partner_tier": "Enterprise", "revenue_share_pct": 0.80, "country_code": "USA", "account_manager": "Sarah Steiner", "contract_status": "ACTIVE", "signed_date": "2016-01-15"},
        {"contract_id": 2, "channel_title": "LastWeekTonight", "partner_tier": "Enterprise", "revenue_share_pct": 0.85, "country_code": "USA", "account_manager": "Michael Brandstetter", "contract_status": "ACTIVE", "signed_date": "2015-04-10"},
        {"contract_id": 3, "channel_title": "Rudy Mancuso", "partner_tier": "Partner", "revenue_share_pct": 0.70, "country_code": "USA", "account_manager": "Sarah Steiner", "contract_status": "ACTIVE", "signed_date": "2016-09-01"},
        {"contract_id": 4, "channel_title": "Good Mythical Morning", "partner_tier": "Enterprise", "revenue_share_pct": 0.75, "country_code": "USA", "account_manager": "David Koch", "contract_status": "ACTIVE", "signed_date": "2014-03-20"},
        {"contract_id": 5, "channel_title": "nigahiga", "partner_tier": "Enterprise", "revenue_share_pct": 0.80, "country_code": "USA", "account_manager": "Sarah Steiner", "contract_status": "ACTIVE", "signed_date": "2013-11-05"},
        {"contract_id": 6, "channel_title": "iJustine", "partner_tier": "Partner", "revenue_share_pct": 0.70, "country_code": "USA", "account_manager": "Elena Weber", "contract_status": "ACTIVE", "signed_date": "2015-08-12"},
        {"contract_id": 7, "channel_title": "Saturday Night Live", "partner_tier": "Enterprise", "revenue_share_pct": 0.85, "country_code": "USA", "account_manager": "Michael Brandstetter", "contract_status": "ACTIVE", "signed_date": "2012-09-18"},
        {"contract_id": 8, "channel_title": "CrazyRussianHacker", "partner_tier": "Partner", "revenue_share_pct": 0.65, "country_code": "USA", "account_manager": "David Koch", "contract_status": "ACTIVE", "signed_date": "2016-06-30"},
        {"contract_id": 9, "channel_title": "20th Century Fox", "partner_tier": "Enterprise", "revenue_share_pct": 0.90, "country_code": "USA", "account_manager": "Michael Brandstetter", "contract_status": "ACTIVE", "signed_date": "2011-01-01"},
        {"contract_id": 10, "channel_title": "Vox", "partner_tier": "Enterprise", "revenue_share_pct": 0.75, "country_code": "USA", "account_manager": "Elena Weber", "contract_status": "ACTIVE", "signed_date": "2015-05-14"},
        {"contract_id": 11, "channel_title": "NFL", "partner_tier": "Enterprise", "revenue_share_pct": 0.90, "country_code": "USA", "account_manager": "Michael Brandstetter", "contract_status": "ACTIVE", "signed_date": "2014-08-01"},
        {"contract_id": 12, "channel_title": "Tom Scott", "partner_tier": "Enterprise", "revenue_share_pct": 0.75, "country_code": "GBR", "account_manager": "Sarah Steiner", "contract_status": "ACTIVE", "signed_date": "2015-01-20"}
    ]


def run_extractor():
    logger.info("=" * 65)
    logger.info("Starte CRM REST-API Extraktor (Multi-Source Ingestion)")
    logger.info("=" * 65)

    records = fetch_contracts_from_api()
    if not records:
        logger.error("Keine Datensaetze erhalten.")
        return

    df = pd.DataFrame(records)

    # Typisierung & Audit-Metadaten
    df["contract_id"] = df["contract_id"].astype(int)
    df["channel_title"] = df["channel_title"].astype(str)
    df["partner_tier"] = df["partner_tier"].astype(str)
    df["revenue_share_pct"] = df["revenue_share_pct"].astype(float)
    df["country_code"] = df["country_code"].astype(str)
    df["account_manager"] = df["account_manager"].astype(str)
    df["contract_status"] = df["contract_status"].astype(str)
    df["signed_date"] = pd.to_datetime(df["signed_date"]).dt.strftime("%Y-%m-%d")
    df["_extracted_at"] = datetime.now(timezone.utc).isoformat()

    # In-Memory Parquet Serialisierung (0 lokale Festplattendateien!)
    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
    parquet_bytes = parquet_buffer.getvalue()
    logger.info(f"Parquet-Datei in-memory erzeugt ({len(parquet_bytes)} Bytes, {len(df)} Zeilen).")

    # Direkt nach Google Cloud Storage streamen
    session = get_gcs_session()
    upload_url = f"https://storage.googleapis.com/upload/storage/v1/b/{GCS_BUCKET}/o?uploadType=media&name={GCS_DEST_BLOB}"
    headers = {"Content-Type": "application/octet-stream"}

    resp = session.post(upload_url, data=parquet_bytes, headers=headers)
    if resp.status_code == 200:
        logger.info(f"Erfolgreich nach GCS hochgeladen: gs://{GCS_BUCKET}/{GCS_DEST_BLOB}")
    else:
        logger.error(f"GCS Upload fehlgeschlagen: {resp.status_code} - {resp.text}")
        raise RuntimeError(f"GCS Upload Fehler: {resp.status_code}")

    logger.info("=" * 65)
    logger.info(f"CRM Ingestion abgeschlossen: {len(df)} Vertraege im GCS Lakehouse gespeichert.")
    logger.info("=" * 65)


if __name__ == "__main__":
    run_extractor()
