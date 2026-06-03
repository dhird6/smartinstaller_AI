#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Registers the Smart Install AI Windows Service (SCM).
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$ServiceScript = Join-Path $ProjectRoot "smartinstall_service.py"
Write-Host "Installing Smart Install AI Windows Service..."
& $Python $ServiceScript install
& $Python $ServiceScript start
Write-Host "Done. Manage with: python smartinstall_service.py stop|restart|remove"
