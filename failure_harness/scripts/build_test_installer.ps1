#Requires -Version 5.1
<#
.SYNOPSIS
    Build TestAppSetup.exe — the failure-injection test application installer.
#>
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
}
if (-not (Test-Path $VenvPython)) {
    Write-Error "Python venv not found. Run: python -m venv .venv && pip install -e ."
}

if (-not $SkipInstall) {
    & $VenvPython -m pip install pyinstaller --quiet
    & $VenvPython -m pip install -e . --quiet
}

$InstallersDir = Join-Path $ProjectRoot "installers"
New-Item -ItemType Directory -Force -Path $InstallersDir | Out-Null

$SpecPath = Join-Path $ProjectRoot "failure_harness\packaging\TestAppSetup.spec"
& $VenvPython -m PyInstaller $SpecPath --noconfirm --distpath $InstallersDir --workpath (Join-Path $ProjectRoot "failure_harness\build")

$ExePath = Join-Path $InstallersDir "TestAppSetup.exe"
if (Test-Path $ExePath) {
    Write-Host "Built: $ExePath" -ForegroundColor Green
} else {
    Write-Error "Build failed - TestAppSetup.exe not found"
}
