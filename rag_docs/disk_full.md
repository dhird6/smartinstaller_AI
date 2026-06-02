# Error: Disk full

## Symptoms
- No space left on device
- Model download fails with storage error

## Root Causes
- Insufficient disk storage for model files
- Default model directory on small system drive

## Diagnosis
- Check free disk space on C: drive
- Identify model storage path: %USERPROFILE%\.ollama\models

## Resolution
- Delete unused models: ollama rm <model-name>
- Move models to a larger drive by setting OLLAMA_MODELS environment variable
- Example: set OLLAMA_MODELS=D:\ollama_models
