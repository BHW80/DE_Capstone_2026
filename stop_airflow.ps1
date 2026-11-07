Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Stoppe Apache Airflow..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

docker compose -f docker/docker-compose-airflow.yml down

Write-Host "`nAirflow erfolgreich gestoppt und Ressourcen freigegeben." -ForegroundColor Green
