param (
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Command = @("plan")
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$TfExe = Join-Path $ScriptDir "terraform\terraform.exe"

if (-not (Test-Path $TfExe)) {
    Write-Host "[FEHLER] terraform.exe nicht gefunden unter: $TfExe" -ForegroundColor Red
    exit 1
}

$cmdString = $Command -join " "
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Ausfuehren: terraform $cmdString (im Ordner infra/)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Fuehrt den Terraform-Befehl mit allen Argumenten im Ordner infra/ aus
& $TfExe "-chdir=infra" @Command
