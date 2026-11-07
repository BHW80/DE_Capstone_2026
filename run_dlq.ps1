Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Dead Letter Queue (DLQ) Consumer..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Nutzt automatisch das venv-Python, falls vorhanden
if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe src/consumer_dlq.py
} else {
    python src/consumer_dlq.py
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDLQ Consumer erfolgreich beendet!" -ForegroundColor Green
    Write-Host "Quarantaene-Daten abgelegt in: data/quarantine/" -ForegroundColor Green
} else {
    Write-Host "`nFehler beim DLQ Consumer (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
}
