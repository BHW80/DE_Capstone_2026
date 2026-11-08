Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Serverless Cloud Pub/Sub Bronze Consumer..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe src/cloud_pubsub_consumer_bronze.py
} else {
    python src/cloud_pubsub_consumer_bronze.py
}
