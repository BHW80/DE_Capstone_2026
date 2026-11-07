Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Streaming Producer (inkl. DLQ & SCD-2 Injection)..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Nutzt automatisch das venv-Python, falls vorhanden
if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe src/producer.py
} else {
    python src/producer.py
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nStreaming erfolgreich beendet!" -ForegroundColor Green
} else {
    Write-Host "`nFehler beim Streaming Producer (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
}
