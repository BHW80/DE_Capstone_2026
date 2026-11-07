Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Bronze Ingestion via Kafka Consumer..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Nutzt automatisch das venv-Python, falls vorhanden
if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe src/consumer_bronze.py
} else {
    python src/consumer_bronze.py
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nBronze Ingestion erfolgreich abgeschlossen!" -ForegroundColor Green
    Write-Host "Rohdaten abgelegt in: data/bronze/" -ForegroundColor Green
} else {
    Write-Host "`nFehler bei der Bronze Ingestion (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
}
