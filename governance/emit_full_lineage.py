# =============================================================================
# DataHub Full Enterprise Lineage Emitter (Release v2.3.0 Complete Star-Schema)
# Verbindet ALLE 13 Knoten aller DREI Quellwelten deterministisch:
#
#   1. Kafka (Streaming)   ──► Pub/Sub ──► GCS Bronze ──┐
#                                                       ├──► GCS Silver ──► BQ silver ──► stg_videos
#   2. Category JSON       ─────────────────────────────┘                                    │
#                                  │                                                         ├──► dim_video
#                                  └──────────────────────────────────► dim_category ────────┼──► dim_date
#                                                                                            │
#   3. MariaDB (OLTP CRM) ──► GCS CRM ──► ext_contracts ──► dim_creator_contract ───────────┘
#                                                                                            │
#                                                                                            ▼
#                                                                                 [dbt Model: fact]
#                                                                                            │
#                                                                                            ▼
#                                                                                 [BQ: fact_video_metrics]
# =============================================================================

import time
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DataHubRestEmitter
from datahub.metadata.schema_classes import (
    AuditStampClass,
    DatasetLineageTypeClass,
    DatasetPropertiesClass,
    UpstreamClass,
    UpstreamLineageClass,
)

def make_upstream(urn: str) -> UpstreamClass:
    return UpstreamClass(
        dataset=urn,
        type=DatasetLineageTypeClass.TRANSFORMED,
        auditStamp=AuditStampClass(
            time=int(time.time() * 1000),
            actor="urn:li:corpUser:dataops_engineer",
        ),
    )

def emit_lineage(emitter: DataHubRestEmitter, downstream_urns: list[str], upstream_urns: list[str]):
    upstreams = [make_upstream(u) for u in upstream_urns]
    for d_urn in downstream_urns:
        mcp = MetadataChangeProposalWrapper(
            entityUrn=d_urn,
            aspect=UpstreamLineageClass(upstreams=upstreams),
        )
        emitter.emit(mcp)

def emit_dataset_props(emitter: DataHubRestEmitter, urn: str, name: str, description: str, platform_type: str):
    mcp = MetadataChangeProposalWrapper(
        entityUrn=urn,
        aspect=DatasetPropertiesClass(
            name=name,
            description=description,
            customProperties={"layer": platform_type},
        ),
    )
    emitter.emit(mcp)

def main():
    emitter = DataHubRestEmitter(gms_server="http://localhost:8080")
    print("=" * 70)
    print("Bilde vollstaendiges Multi-Source Star-Schema inkl. JSON-Quelle ab...")
    print("=" * 70)

    # 1. URNs fuer alle drei Quellsysteme & Schichten
    # Quelle 1: Streaming
    URN_KAFKA = "urn:li:dataset:(urn:li:dataPlatform:kafka,topic_ingest,PROD)"
    URN_PUBSUB = "urn:li:dataset:(urn:li:dataPlatform:pubsub,topic-youtube-ingest,PROD)"
    URN_GCS_BRONZE = "urn:li:dataset:(urn:li:dataPlatform:gcs,lakehouse-youtube-cloudanalytics-514018/bronze,PROD)"

    # Quelle 2: Referenzdaten JSON
    URN_CAT_JSON = "urn:li:dataset:(urn:li:dataPlatform:file,data/raw/US_category_id.json,PROD)"

    # Silver & Staging
    URN_GCS_SILVER = "urn:li:dataset:(urn:li:dataPlatform:gcs,lakehouse-youtube-cloudanalytics-514018/silver,PROD)"
    URN_BQ_SILVER = "urn:li:dataset:(urn:li:dataPlatform:bigquery,cloudanalytics-514018.youtube_analytics.silver_videos,PROD)"
    URN_STG = "urn:li:dataset:(urn:li:dataPlatform:bigquery,cloudanalytics-514018.youtube_analytics.stg_videos,PROD)"

    # Quelle 3: OLTP CRM (MariaDB)
    URN_MARIADB = "urn:li:dataset:(urn:li:dataPlatform:mysql,usrdb_welbmqup.creator_contracts,PROD)"
    URN_GCS_CRM = "urn:li:dataset:(urn:li:dataPlatform:gcs,lakehouse-youtube-cloudanalytics-514018/bronze/crm_contracts,PROD)"
    URN_EXT_CRM = "urn:li:dataset:(urn:li:dataPlatform:bigquery,cloudanalytics-514018.youtube_analytics.ext_creator_contracts,PROD)"
    URN_DIM_CRM = "urn:li:dataset:(urn:li:dataPlatform:bigquery,cloudanalytics-514018.youtube_analytics.dim_creator_contract,PROD)"

    # Die restlichen 3 Dimensionen
    URN_DIM_VIDEO = "urn:li:dataset:(urn:li:dataPlatform:bigquery,cloudanalytics-514018.youtube_analytics.dim_video,PROD)"
    URN_DIM_CAT = "urn:li:dataset:(urn:li:dataPlatform:bigquery,cloudanalytics-514018.youtube_analytics.dim_category,PROD)"
    URN_DIM_DATE = "urn:li:dataset:(urn:li:dataPlatform:bigquery,cloudanalytics-514018.youtube_analytics.dim_date,PROD)"

    # Zentrale Faktentabelle
    URN_FACT_DBT = "urn:li:dataset:(urn:li:dataPlatform:dbt,cloudanalytics-514018.youtube_analytics.fact_video_metrics,PROD)"
    URN_FACT_BQ = "urn:li:dataset:(urn:li:dataPlatform:bigquery,cloudanalytics-514018.youtube_analytics.fact_video_metrics,PROD)"

    # 2. Materialisiere alle 13 Knoten mit Titeln & Beschreibungen
    print("\n[1/3] Registriere Knoten in DataHub...")
    emit_dataset_props(emitter, URN_KAFKA, "topic_ingest", "On-Premises Apache Kafka (127.0.0.1:9092, KRaft Mode)", "Source Streaming")
    emit_dataset_props(emitter, URN_CAT_JSON, "US_category_id.json", "Lokale Referenz-Metadaten fuer YouTube-Kategorien (JSON)", "Source Reference Data")
    emit_dataset_props(emitter, URN_MARIADB, "creator_contracts", "OLTP MariaDB @ weltler.at (Port 3306 geschuetzt)", "Source OLTP")

    emit_dataset_props(emitter, URN_PUBSUB, "topic-youtube-ingest", "Google Cloud Pub/Sub Ingestion Topic", "Streaming Broker")
    emit_dataset_props(emitter, URN_GCS_BRONZE, "lakehouse/bronze", "GCS Medallion Bronze Parquet", "Raw Storage")
    emit_dataset_props(emitter, URN_GCS_SILVER, "lakehouse/silver", "GCS Medallion Silver Parquet & Iceberg V2", "Lakehouse Silver")
    emit_dataset_props(emitter, URN_GCS_CRM, "lakehouse/bronze/crm_contracts", "GCS CRM Contracts Parquet Storage", "Lakehouse CRM")
    emit_dataset_props(emitter, URN_EXT_CRM, "ext_creator_contracts", "BigQuery BigLake External Table", "External Table")

    emit_dataset_props(emitter, URN_DIM_CRM, "dim_creator_contract", "Conformed Dimension: Creator Contracts", "Dimension")
    emit_dataset_props(emitter, URN_DIM_CAT, "dim_category", "Conformed Dimension: Video Categories", "Dimension")
    emit_dataset_props(emitter, URN_DIM_DATE, "dim_date", "Conformed Dimension: Calendar Dates", "Dimension")
    emit_dataset_props(emitter, URN_DIM_VIDEO, "dim_video", "SCD-2 Dimension: Historical Video Titles", "Dimension SCD-2")
    emit_dataset_props(emitter, URN_FACT_BQ, "fact_video_metrics", "Zentrale Kimball Faktentabelle mit Payout-KPI", "Fact Table")

    # 3. Kanten deterministisch verdrahten
    print("\n[2/3] Verbinde Streaming- & Referenzdaten-Pfad...")
    emit_lineage(emitter, [URN_PUBSUB], [URN_KAFKA])
    emit_lineage(emitter, [URN_GCS_BRONZE], [URN_PUBSUB])
    # GCS Silver entsteht aus dem Join von Bronze-Streaming + Category JSON!
    emit_lineage(emitter, [URN_GCS_SILVER], [URN_GCS_BRONZE, URN_CAT_JSON])
    emit_lineage(emitter, [URN_BQ_SILVER], [URN_GCS_SILVER])
    emit_lineage(emitter, [URN_STG], [URN_BQ_SILVER])

    print("\n[3/3] Verbinde Kimball Star-Schema & CRM-Pfad...")
    # CRM Pfad (MariaDB -> GCS CRM -> External Table -> Conformed Dim)
    emit_lineage(emitter, [URN_GCS_CRM], [URN_MARIADB])
    emit_lineage(emitter, [URN_EXT_CRM], [URN_GCS_CRM])
    emit_lineage(emitter, [URN_DIM_CRM], [URN_EXT_CRM])

    # Dimensionen aus Staging & JSON speisen
    emit_lineage(emitter, [URN_DIM_VIDEO], [URN_STG])
    emit_lineage(emitter, [URN_DIM_DATE], [URN_STG])
    # dim_category stammt fachlich aus Staging und den JSON-Referenzdaten:
    emit_lineage(emitter, [URN_DIM_CAT], [URN_STG, URN_CAT_JSON])

    # Faktentabelle: dbt-Modell -> BigQuery Dataset Kasten
    fact_upstreams = [URN_DIM_VIDEO, URN_DIM_CAT, URN_DIM_DATE, URN_DIM_CRM, URN_STG]
    emit_lineage(emitter, [URN_FACT_DBT], fact_upstreams)
    emit_lineage(emitter, [URN_FACT_BQ], [URN_FACT_DBT])

    print("\n" + "=" * 70)
    print(">>> ERFOLG: Alle DREI Datenquellen (Kafka, MariaDB, JSON) sind verdrahtet! <<<")
    print("=" * 70)

if __name__ == "__main__":
    main()
