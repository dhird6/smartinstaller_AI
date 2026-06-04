# QA helper: sleeps so Smart Installer can inject test issues during_install.
# Usage: from Installation Center, browse to this script's .bat wrapper or any long-running installer.
param([int]$Seconds = 45)
Write-Host "Smart Installer test installer — waiting $Seconds seconds..."
Start-Sleep -Seconds $Seconds
Write-Host "Test installer finished (exit 0)."
exit 0
