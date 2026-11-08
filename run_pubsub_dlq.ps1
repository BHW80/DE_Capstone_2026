Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Serverless Cloud Pub/Sub DLQ Consumer (Quarantaene)..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe src/cloud_pubsub_consumer_dlq.py
} else {
    python src/cloud_pubsub_consumer_dlq.py
}
