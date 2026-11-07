Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Apache Airflow (Scheduler, Webserver, Postgres)..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

docker compose -f docker/docker-compose-airflow.yml up -d

Write-Host "`nAirflow-Dienste gestartet!" -ForegroundColor Green
Write-Host "Dashboard wird unter: http://localhost:8085 erreichbar sein" -ForegroundColor Yellow
Write-Host "Login: admin / admin" -ForegroundColor Yellow
Write-Host "(Hinweis: Beim allerersten Start dauert die DB-Initialisierung ca. 30-45 Sekunden)" -ForegroundColor Gray
