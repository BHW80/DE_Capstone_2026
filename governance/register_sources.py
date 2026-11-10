# DataHub Metadata Emitter: Registriert Root-Quellsysteme (MariaDB & Kafka)
# Weist ihnen Namen, Beschreibungen und Plattform-Eigenschaften zu.

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DataHubRestEmitter
from datahub.metadata.schema_classes import DatasetPropertiesClass

def main():
    emitter = DataHubRestEmitter(gms_server="http://localhost:8080")

    # 1. Externe MariaDB Tabelle als vollwertiges Dataset registrieren
    print("Registriere MariaDB OLTP Source @ weltler.at...")
    emitter.emit(
        MetadataChangeProposalWrapper(
            entityUrn="urn:li:dataset:(urn:li:dataPlatform:mysql,usrdb_welbmqup.creator_contracts,PROD)",
            aspect=DatasetPropertiesClass(
                name="creator_contracts",
                description="Relationale OLTP Creator-Vertraege & Stammdaten (MariaDB 10.x gehostet auf www.weltler.at)",
                customProperties={
                    "host": "www.weltler.at",
                    "database": "usrdb_welbmqup",
                    "table": "creator_contracts",
                    "source_type": "OLTP SaaS CRM"
                },
            ),
        )
    )

    # 2. Lokales Apache Kafka Ingest Topic als vollwertiges Dataset registrieren
    print("Registriere On-Premises Apache Kafka Topic...")
    emitter.emit(
        MetadataChangeProposalWrapper(
            entityUrn="urn:li:dataset:(urn:li:dataPlatform:kafka,topic_ingest,PROD)",
            aspect=DatasetPropertiesClass(
                name="topic_ingest",
                description="On-Premises Apache Kafka Streaming Broker (127.0.0.1:9092, KRaft Mode)",
                customProperties={
                    "broker": "127.0.0.1:9092",
                    "topic": "topic_ingest",
                    "source_type": "Edge Streaming Buffer"
                },
            ),
        )
    )

    print("\n>>> ERFOLG: MariaDB (MySQL) und Kafka wurden als offizielle Plattformen in DataHub registriert! <<<")

if __name__ == "__main__":
    main()
