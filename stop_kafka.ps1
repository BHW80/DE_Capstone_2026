Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Stoppe Apache Kafka Broker & Kafka-UI..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

docker compose -f docker/docker-compose-kafka.yml down

Write-Host "`nKafka & Kafka-UI erfolgreich gestoppt." -ForegroundColor Green
