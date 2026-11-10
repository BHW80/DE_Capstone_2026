Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Hybrid Bridge: On-Premises Kafka -> Google Cloud Pub/Sub..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe src/bridge_kafka_to_pubsub.py
} else {
    python src/bridge_kafka_to_pubsub.py
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[FEHLER] Hybrid Bridge Uebertragung fehlgeschlagen!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[ERFOLG] Hybrid Bridge Uebertragung erfolgreich abgeschlossen!" -ForegroundColor Green
