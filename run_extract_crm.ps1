Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte CRM REST-API Extraktor (Multi-Source Ingestion)..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe src/cloud_crm_extractor.py
} else {
    python src/cloud_crm_extractor.py
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[FEHLER] CRM API Extraktion fehlgeschlagen!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[ERFOLG] CRM Daten erfolgreich in GCS Bronze geladen!" -ForegroundColor Green
