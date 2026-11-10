# =============================================================================
# DataHub Governance & Lineage Runner (Release v3.0.0)
# Steuert DataHub Quickstart, REST Lineage Emission & dbt Test Assertions
# =============================================================================

[CmdletBinding()]
param (
    [ValidateSet("start", "stop", "emit", "ingest-dbt", "status")]
    [string]$Action = "emit"
)

$ErrorActionPreference = "Stop"

switch ($Action) {
    "start" {
        Write-Host "Starte DataHub Docker Quickstart Stack (Port 9002)..." -ForegroundColor Cyan
        datahub docker quickstart
    }
    "stop" {
        Write-Host "Stoppe DataHub Docker Quickstart Container..." -ForegroundColor Yellow
        datahub docker quickstart --stop
    }
    "emit" {
        Write-Host "Emittiere 13-Knoten Multi-Source Lineage an DataHub GMS (Port 8080)..." -ForegroundColor Cyan
        & python "$PSScriptRoot\governance\emit_full_lineage.py"
    }
    "ingest-dbt" {
        Write-Host "Ingestiere dbt Core Manifest & 15 Quality Test Assertions..." -ForegroundColor Cyan
        datahub ingest -c "$PSScriptRoot\governance\recipe_dbt.yaml"
    }
    "status" {
        Write-Host "Pruefe DataHub Container Status..." -ForegroundColor Cyan
        docker ps --filter "name=datahub"
    }
}
