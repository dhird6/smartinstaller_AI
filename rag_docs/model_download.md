# Error: Model download interrupted

## Symptoms
- Download stops unexpectedly
- ollama pull hangs or fails mid-download

## Root Causes
- Network instability
- Disk full during download
- Connection timeout

## Diagnosis
- Check available storage (dir C:\)
- Verify internet connection stability
- Re-run ollama pull to check resume behavior

## Resolution
- Free disk space before pulling large models
- Retry ollama pull (Ollama resumes partial downloads)
- Use a stable wired connection for large models
