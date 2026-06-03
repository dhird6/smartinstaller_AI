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
