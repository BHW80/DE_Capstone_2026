Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starte Gold Transformation via Apache Spark Container..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

docker compose -f docker/docker-compose-spark.yml run --rm spark /opt/spark/bin/spark-submit /app/src/transform_gold.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nGold Spark Job erfolgreich abgeschlossen!" -ForegroundColor Green
    Write-Host "Marts abgelegt in: data/gold/" -ForegroundColor Green
} else {
    Write-Host "`nFehler beim Ausfuehren des Gold Spark Jobs (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
}
