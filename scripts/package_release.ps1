# Package SmartInstallAI.exe for distribution to another Windows PC.
# Does not modify application UI — copies the built executable and optional sidecar files.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$exePath = Join-Path $projectRoot "dist\SmartInstallAI.exe"
if (-not (Test-Path $exePath)) {
    Write-Error "Build first: .\scripts\build_desktop.ps1"
}

$stamp = Get-Date -Format "yyyyMMdd"
$releaseDir = Join-Path $projectRoot "release\SmartInstallAI_$stamp"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

Copy-Item $exePath (Join-Path $releaseDir "SmartInstallAI.exe") -Force

$configSrc = Join-Path $projectRoot "config\smartinstall.config.json"
if (Test-Path $configSrc) {
    $configDest = Join-Path $releaseDir "config"
    New-Item -ItemType Directory -Force -Path $configDest | Out-Null
    Copy-Item $configSrc (Join-Path $configDest "smartinstall.config.json") -Force
}

$logoSrc = Join-Path $projectRoot "images\logo.png"
if (Test-Path $logoSrc) {
    $imagesDest = Join-Path $releaseDir "images"
    New-Item -ItemType Directory -Force -Path $imagesDest | Out-Null
    Copy-Item $logoSrc (Join-Path $imagesDest "logo.png") -Force
}

$readme = @"
SmartInstall AI - Portable package
==================================

1. Copy this entire folder to the target Windows 10/11 PC.
2. Double-click SmartInstallAI.exe (Run as Administrator recommended).
3. For full AI troubleshooting, install Ollama on that PC and run:
     ollama pull phi3:mini
     ollama pull nomic-embed-text
   Keep Ollama running while using AI features.

Folders (installers, reports, sessions, logs) are created next to the EXE on first run.

Optional: edit config\smartinstall.config.json before first launch to change settings.
Set autoLaunchDemoInstallOnStartup to false to skip the bundled TestApp demo.

No Python required on the target machine.
"@
$readme | Out-File -FilePath (Join-Path $releaseDir "README-DEPLOY.txt") -Encoding utf8

Write-Host "Release package ready:"
Write-Host $releaseDir
Write-Host "Zip this folder and share it with the other PC."
