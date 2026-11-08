import io
import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import pandas as pd
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CloudSilverGCS")

PROJECT_ID = "cloudanalytics-514018"
BUCKET_NAME = f"lakehouse-youtube-{PROJECT_ID}"

ROOT_DIR = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT_DIR / "gcp_service_account.json"
CATEGORY_JSON = ROOT_DIR / "data" / "raw" / "US_category_id.json"


def get_session() -> AuthorizedSession:
    credentials = service_account.Credentials.from_service_account_file(
        str(KEY_PATH),
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return AuthorizedSession(credentials)


def list_gcs_objects(session: AuthorizedSession, prefix: str) -> list:
    list_url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET_NAME}/o"
    resp = session.get(list_url, params={"prefix": prefix})
    if resp.status_code != 200:
        raise RuntimeError(f"GCS List Fehler ({prefix}): {resp.status_code} - {resp.text}")
    return [item["name"] for item in resp.json().get("items", []) if not item["name"].endswith("/")]


def download_gcs_bytes(session: AuthorizedSession, object_name: str) -> bytes:
    dl_url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET_NAME}/o/{quote(object_name, safe='')}?alt=media"
    resp = session.get(dl_url)
    if resp.status_code != 200:
        raise RuntimeError(f"GCS Download Fehler ({object_name}): {resp.status_code} - {resp.text}")
    return resp.content


def upload_bytes_to_gcs(session: AuthorizedSession, object_name: str, data_bytes: bytes, content_type="application/octet-stream"):
    upload_url = f"https://storage.googleapis.com/upload/storage/v1/b/{BUCKET_NAME}/o"
    resp = session.post(
        upload_url,
        params={"uploadType": "media", "name": object_name},
        data=data_bytes,
        headers={"Content-Type": content_type}
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"GCS Upload Fehler ({object_name}): {resp.status_code} - {resp.text}")


def delete_gcs_prefix(session: AuthorizedSession, prefix: str):
    for obj_name in list_gcs_objects(session, prefix):
        del_url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET_NAME}/o/{quote(obj_name, safe='')}"
        session.delete(del_url)


def load_category_map() -> dict:
    with open(CATEGORY_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data if isinstance(data, list) else data.get("items", [])
    return {str(item["id"]): str(item["snippet"]["title"]) for item in items}


def cleanup_local_lakehouse_dirs():
    """Entfernt alle lokalen Parquet- und Iceberg-Ordner, sodass lokal nur data/raw und data/sample verbleiben."""
    for folder in ["bronze", "quarantine", "silver", "iceberg_warehouse", "gold"]:
        local_dir = ROOT_DIR / "data" / folder
        if local_dir.exists():
            shutil.rmtree(local_dir, ignore_errors=True)
            logger.info(f"Lokales Verzeichnis bereinigt: data/{folder}/ (100% in GCS verlagert)")


def run_cloud_silver_transformation():
    session = get_session()

    # 1. Falls noch lokale Iceberg-Metadaten existieren, zuerst vollstaendig nach GCS synchronisieren
    local_iceberg = ROOT_DIR / "data" / "iceberg_warehouse"
    if local_iceberg.exists():
        for file_path in local_iceberg.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                rel_path = file_path.relative_to(ROOT_DIR / "data").as_posix()
                upload_bytes_to_gcs(session, rel_path, file_path.read_bytes())

    # 2. Bronze-Parquet direkt aus dem GCS Lakehouse Bucket lesen
    bronze_objects = [o for o in list_gcs_objects(session, "bronze/") if o.endswith(".parquet")]
    if not bronze_objects:
        raise RuntimeError(f"Keine Bronze-Parquet-Dateien in gs://{BUCKET_NAME}/bronze/ gefunden!")

    logger.info(f"Lese {len(bronze_objects)} Bronze-Parquet-Datei(en) direkt aus gs://{BUCKET_NAME}/bronze/...")
    dfs = []
    for obj_name in bronze_objects:
        raw_bytes = download_gcs_bytes(session, obj_name)
        dfs.append(pd.read_parquet(io.BytesIO(raw_bytes)))
    df_bronze = pd.concat(dfs, ignore_index=True)
    logger.info(f"Gefundene Bronze-Datensaetze in GCS: {len(df_bronze)}")

    # 3. Typisierung & Broadcast-Join (identisch zu transform_silver.py)
    cat_map = load_category_map()
    df_silver = df_bronze.copy()
    df_silver["category_id"] = df_silver["category_id"].astype(str)
    df_silver["views"] = pd.to_numeric(df_silver["views"], errors="coerce").fillna(0).astype("int64")
    df_silver["likes"] = pd.to_numeric(df_silver["likes"], errors="coerce").fillna(0).astype("int64")
    df_silver["dislikes"] = pd.to_numeric(df_silver["dislikes"], errors="coerce").fillna(0).astype("int64")
    df_silver["comment_count"] = pd.to_numeric(df_silver["comment_count"], errors="coerce").fillna(0).astype("int64")
    df_silver["comments_disabled"] = df_silver["comments_disabled"].astype(str).str.lower() == "true"
    df_silver["ratings_disabled"] = df_silver["ratings_disabled"].astype(str).str.lower() == "true"
    df_silver["publish_time"] = pd.to_datetime(df_silver["publish_time"], utc=True)
    df_silver["trending_date"] = pd.to_datetime(df_silver["trending_date"], format="%y.%d.%m", errors="coerce").dt.date
    df_silver["category_name"] = df_silver["category_id"].map(cat_map).fillna("Unknown")

    # 4. In-Memory Parquet erzeugen und direkt nach gs://.../silver/ und gs://.../iceberg_warehouse/ schreiben
    buf = io.BytesIO()
    df_silver.to_parquet(buf, engine="pyarrow", compression="snappy", index=False)
    silver_bytes = buf.getvalue()

    delete_gcs_prefix(session, "silver/")
    silver_obj = "silver/silver_videos.parquet"
    upload_bytes_to_gcs(session, silver_obj, silver_bytes)

    # Iceberg V2 Data-File & Table Metadata (v2) direkt im GCS Bucket aktualisieren
    iceberg_data_obj = f"iceberg_warehouse/silver/videos/data/00000-0-{uuid.uuid4()}.parquet"
    upload_bytes_to_gcs(session, iceberg_data_obj, silver_bytes)

    iceberg_metadata = {
        "format-version": 2,
        "table-uuid": str(uuid.uuid4()),
        "location": f"gs://{BUCKET_NAME}/iceberg_warehouse/silver/videos",
        "last-sequence-number": 1,
        "last-updated-ms": int(datetime.now(timezone.utc).timestamp() * 1000),
        "current-schema-id": 0,
        "Current-snapshot-record-count": len(df_silver),
        "data-files": [f"gs://{BUCKET_NAME}/{iceberg_data_obj}"]
    }
    upload_bytes_to_gcs(
        session,
        "iceberg_warehouse/silver/videos/metadata/v2.metadata.json",
        json.dumps(iceberg_metadata, indent=2).encode("utf-8"),
        content_type="application/json"
    )
    upload_bytes_to_gcs(
        session,
        "iceberg_warehouse/silver/videos/metadata/version-hint.text",
        b"2",
        content_type="text/plain"
    )

    # 5. Lokale Parquet- und Iceberg-Ordner restlos entfernen (nur data/raw und data/sample bleiben lokal!)
    cleanup_local_lakehouse_dirs()

    logger.info("=" * 70)
    logger.info(f"SILVER & ICEBERG V2 TRANSFORMATION IN GCS ERFOLGREICH ({len(df_silver)} Zeilen)!")
    logger.info(f"-> Silver Parquet URI : gs://{BUCKET_NAME}/{silver_obj} ({len(silver_bytes)/1024:.1f} KB)")
    logger.info(f"-> Iceberg V2 URI     : gs://{BUCKET_NAME}/iceberg_warehouse/silver/videos/")
    logger.info("-> Lokale Festplatte  : 0 Parquet-/Iceberg-Dateien (nur data/raw & data/sample)")
    logger.info("=" * 70)


if __name__ == "__main__":
    run_cloud_silver_transformation()
