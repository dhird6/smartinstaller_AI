# Error: could not connect to a running Ollama instance

## Symptoms
- Warning: could not connect to a running Ollama instance
- connectex: No connection could be made

## Root Causes
- Server not started
- Server crashed
- Port inaccessible
- Firewall block
- Wrong endpoint

## Diagnosis
- Run: ollama serve
- Open http://127.0.0.1:11434
- Check tasklist
- Check port 11434

## Resolution
- Start Ollama service
- Restart system
- Verify firewall rules
- Allow firewall access
- Correct endpoint URL
