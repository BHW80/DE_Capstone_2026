Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Silver Transformation via Apache Spark Container..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

docker compose -f docker/docker-compose-spark.yml run --rm spark /opt/spark/bin/spark-submit /app/src/transform_silver.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nSpark Job erfolgreich abgeschlossen!" -ForegroundColor Green
    Write-Host "Ergebnis abgelegt in: data/silver/" -ForegroundColor Green
} else {
    Write-Host "`nFehler beim Ausfuehren des Spark Jobs (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
}
