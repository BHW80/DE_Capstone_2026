Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Cloud Release nach Google BigQuery..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Nutzt das venv-Python mit installiertem google-cloud-bigquery
if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe src/cloud_loader_bigquery.py
} else {
    python src/cloud_loader_bigquery.py
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nCloud Release nach Google BigQuery erfolgreich!" -ForegroundColor Green
    Write-Host "BigQuery Console: https://console.cloud.google.com/bigquery?project=cloudanalytics-514018" -ForegroundColor Yellow
} else {
    Write-Host "`nFehler beim Cloud Release (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
}
