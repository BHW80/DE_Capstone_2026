Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Stoppe Observability Stack (Prometheus & Grafana)..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

docker compose -f docker/docker-compose-monitoring.yml down

Write-Host "`nPrometheus & Grafana erfolgreich gestoppt." -ForegroundColor Green
