# Error: Port 11434 already in use

## Symptoms
- bind: address already in use
- Ollama fails to start because port is taken

## Root Causes
- Another Ollama instance already running
- Different application occupying port 11434

## Diagnosis
- Run: netstat -ano | findstr 11434
- Identify PID using the port
- Run: tasklist | findstr <PID>

## Resolution
- Kill conflicting process: taskkill /PID <PID> /F
- Change Ollama port: set OLLAMA_HOST=127.0.0.1:11435
- Restart system to clear stale processes
