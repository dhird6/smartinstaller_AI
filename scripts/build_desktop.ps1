# Build SmartInstallAI.exe (Windows desktop bundle)
param(
    [switch]$Console
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Error "Virtual environment not found. Run: python -m venv .venv"
}

# Close a running build output so PyInstaller can overwrite the exe.
Get-Process -Name "SmartInstallAI" -ErrorAction SilentlyContinue | Stop-Process -Force

.\.venv\Scripts\Activate.ps1
pip install -e ".[desktop]" pyinstaller -q

# Bundle TestApp failure-injection installer into the desktop EXE.
$buildTestApp = Join-Path $projectRoot "failure_harness\scripts\build_test_installer.ps1"
if (Test-Path $buildTestApp) {
    Write-Host "Building bundled TestAppSetup.exe..."
    & $buildTestApp -SkipInstall
    if (-not (Test-Path (Join-Path $projectRoot "installers\TestAppSetup.exe"))) {
        Write-Error "TestAppSetup.exe build failed — required for bundled desktop EXE."
    }
}

$specPath = Join-Path $projectRoot "packaging\SmartInstallAI.spec"
if ($Console) {
    Write-Host "Building windowed executable (use spec console flag manually for debug)."
}

pyinstaller --noconfirm --clean $specPath

$exePath = Join-Path $projectRoot "dist\SmartInstallAI.exe"
if (-not (Test-Path $exePath)) {
    Write-Error "Build failed: executable not found."
}
Write-Host "Build complete: $exePath"
Write-Host "Bundled: Smart Installer UI + TestAppSetup.exe + failure scenarios"
