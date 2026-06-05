#Requires -Version 5.1
<#
.SYNOPSIS
    Run the Smart Installer Failure Injection & RAG Validation Harness.
#>
param(
    [string]$Scenario = "",
    [switch]$ListScenarios,
    [switch]$Phase1Only,
    [switch]$RunAll,
    [switch]$BuildTestApp
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = "python"
}

if ($BuildTestApp) {
    & (Join-Path $PSScriptRoot "build_test_installer.ps1")
}

$Args = @("failure_harness/run_harness.py")
if ($ListScenarios) { $Args += "--list-scenarios" }
if ($Phase1Only) { $Args += "--phase1-only" }
if ($RunAll) { $Args += "--run-all" }
if ($Scenario) { $Args += "--scenario", $Scenario }

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
& $VenvPython @Args
exit $LASTEXITCODE
