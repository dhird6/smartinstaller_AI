# Error: No compatible GPU found

## Symptoms
- No compatible GPUs found

## Root Causes
- Unsupported GPU model
- Driver issue
- GPU not detected by Ollama

## Diagnosis
- Check GPU model compatibility
- Verify driver version
- Run: nvidia-smi (for NVIDIA GPUs)

## Resolution
- Update GPU drivers
- Use CPU inference as fallback (set OLLAMA_NUM_GPU=0)
- Verify GPU is supported by Ollama
