param (
    [string]$Command = "debug"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$DbtExe = Join-Path $ScriptDir ".venv\Scripts\dbt.exe"

if (-not (Test-Path $DbtExe)) {
    Write-Host "[FEHLER] dbt nicht in .venv gefunden unter: $DbtExe" -ForegroundColor Red
    exit 1
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Ausfuehren: dbt $Command" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Fuehrt den dbt-Befehl mit den festgelegten Projekt- und Profilpfaden aus
& $DbtExe $Command --project-dir dbt --profiles-dir dbt
