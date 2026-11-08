Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Starte Cloud Silver & Apache Iceberg V2 Transformation (100% GCS)..." -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

& "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\src\cloud_silver_gcs.py"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nSilver & Iceberg V2 Transformation erfolgreich in GCS abgeschlossen!" -ForegroundColor Green
} else {
    Write-Host "`nFehler bei der Silver Transformation (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
