Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Serverless Cloud Pub/Sub Producer (inkl. DLQ & SCD-2)..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe src/cloud_pubsub_producer.py
} else {
    python src/cloud_pubsub_producer.py
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nCloud Pub/Sub Streaming erfolgreich beendet!" -ForegroundColor Green
} else {
    Write-Host "`nFehler beim Cloud Pub/Sub Producer (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
}
