Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Serverless Google Cloud Workflow..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Nutzt automatisch das venv-Python
if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe src/cloud_workflow_runner.py
} else {
    python src/cloud_workflow_runner.py
}
