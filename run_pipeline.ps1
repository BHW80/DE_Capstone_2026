Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "STARTE KOMPLETTE END-TO-END CLOUD DATAOPS PIPELINE (v2.1.0)" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

& "$PSScriptRoot\run_pubsub_producer.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& "$PSScriptRoot\run_pubsub_bronze.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& "$PSScriptRoot\run_pubsub_dlq.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& "$PSScriptRoot\run_silver.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& "$PSScriptRoot\run_workflow.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=====================================================================" -ForegroundColor Green
Write-Host "KOMPLETTE END-TO-END CLOUD PIPELINE ERFOLGREICH ABGESCHLOSSEN!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
