Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Apache Kafka Broker (KRaft) & Kafka-UI..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

docker compose -f docker/docker-compose-kafka.yml up -d

Write-Host "`nKafka Streaming-Infrastruktur gestartet!" -ForegroundColor Green
Write-Host "-> Kafka Broker: 127.0.0.1:9092" -ForegroundColor Yellow
Write-Host "-> Kafka-UI:     http://localhost:8080" -ForegroundColor Yellow
