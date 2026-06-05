# Category: AUTOCAD_LICENSING_FAILURE

## Error Signature
- AdskLicensingService failed to start
- FlexNet error code -15 (cannot connect to license server)
- FlexNet error code -96 (license server machine is down or not responding)
- FlexNet error code -97 (wrong hostid on SERVER line in license file)
- FlexNet error code -1 (cannot find license file)
- FlexNet error code -4 (licensed number of users already reached)
- License validation failed
- License server unreachable on port 27000
- Cannot connect to license server on port 27000
- Clock skew detected (system time mismatch > 5 minutes)
- Entitlement not found
- ADSKFLEX_LICENSE_FILE not set
- AdskLicensingAgent error
- Licensing daemon lmgrd not running
- FlexLM license manager error

## Meaning
Autodesk AutoCAD, Revit, Inventor or related product failed to activate or launch because
AdskLicensingService, FlexNet, or ADLM licensing daemon could not validate the license.
This is a licensing service failure — NOT an Ollama or general network connectivity issue.

## Common Causes
- AdskLicensingService (Windows service) is stopped or crashed
- FlexNet licensing daemon (lmgrd/adskflex) is not running on license server
- Network license server is unreachable on port 27000 (default FlexLM port)
- System clock is out of sync (clock skew > 5 minutes causes FlexNet -96 error)
- Autodesk subscription expired or entitlement revoked
- License file (*.lic) is corrupted, missing, or moved
- ADSKFLEX_LICENSE_FILE environment variable points to wrong path
- Firewall or antivirus blocking port 27000 or AdskLicensingService process
- Autodesk Access or ODIS service conflict with AdskLicensingService
- Concurrent Autodesk version conflict (two AdskLicensingService versions installed)

## Recommended Actions

### Step 1 — Check AdskLicensingService status
```
sc query AdskLicensingService
net start AdskLicensingService
```

### Step 2 — Repair AdskLicensingService
Run Autodesk Licensing Repair Tool:
- Download from Autodesk support: Autodesk_Licensing_Repair_Tool.exe
- Or reinstall via: Autodesk Access > Repair

### Step 3 — Sync system clock (fixes FlexNet -96 clock skew)
```
w32tm /resync
w32tm /query /status
```

### Step 4 — Verify license server reachability on port 27000
```
netstat -ano | findstr 27000
telnet <license-server-hostname> 27000
```

### Step 5 — Run LMTOOLS to diagnose FlexNet
- Open LMTOOLS (C:\Program Files\Autodesk\Network License Manager\lmtools.exe)
- Check "Server Status" tab → Start Server
- Check "Config Services" tab → verify path to license file (*.lic)

### Step 6 — Check ADSKFLEX_LICENSE_FILE
```
echo %ADSKFLEX_LICENSE_FILE%
set ADSKFLEX_LICENSE_FILE=<port>@<server-hostname>
```

### Step 7 — Clear corrupted ADLM data
```
del /Q "%ProgramData%\Autodesk\Adlm\*"
net start AdskLicensingService
```

### Step 8 — Firewall exception for port 27000
- Add inbound and outbound rule for TCP port 27000 in Windows Firewall
- Allow AdskLicensingService.exe in antivirus/EDR exclusions

## Log Files
- AdskLicensingService logs: %ProgramData%\Autodesk\Adlm\
- FlexNet debug log: %TEMP%\flexnet.log
- Autodesk installer logs: %TEMP%\Autodesk\

## Verification Commands
```
sc query AdskLicensingService
w32tm /query /status
netstat -ano | findstr 27000
dir "%ProgramData%\Autodesk\Adlm\"
```

## Confidence Scoring
- High: FlexNet error code (-15, -96, -97), "AdskLicensingService failed", or clock skew in logs
- High: "License server unreachable on port 27000" or "Cannot connect to FlexNet"
- Medium: Product launches but immediately asks for activation repeatedly
- Low: Generic Autodesk product crash without licensing error messages

## Related Categories
- AUTOCAD_SERVICE_FAILURE — when AdskLicensingService stops after install
- AUTOCAD_ENTERPRISE_DEPLOYMENT_FAILURE — when network license server is centrally managed
- AUTOCAD_OS_LEVEL_FAILURE — when system time/WMI issues affect licensing
