# Error: timed out waiting for server to start

## Symptoms
- Error: timed out waiting for server to start

## Root Causes
- Ollama daemon not running
- Port conflict
- Service crash

## Diagnosis
- Run: ollama serve
- Check logs
- Verify port 11434 availability

## Resolution
- Start server manually
- Kill conflicting processes
- Restart Ollama
