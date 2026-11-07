Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Observability Stack (Prometheus & Grafana)..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

docker compose -f docker/docker-compose-monitoring.yml up -d

Write-Host "`nMonitoring-Dienste gestartet!" -ForegroundColor Green
Write-Host "-> Prometheus Dashboard: http://localhost:9090" -ForegroundColor Yellow
Write-Host "-> Grafana Dashboard:    http://localhost:3000 (Login: admin / admin)" -ForegroundColor Yellow
