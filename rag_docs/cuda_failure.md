# Error: CUDA initialization failed

## Symptoms
- CUDA initialization failed
- ROCm initialization failed
- amdgpu: ROCm initialization failed on device index 0

## Root Causes
- Driver mismatch
- CUDA runtime issue
- Incompatible GPU architecture (e.g., RDNA2 unsupported)

## Diagnosis
- Run: nvidia-smi
- Verify driver installation and version
- Check CUDA toolkit compatibility

## Resolution
- Update NVIDIA drivers to latest version
- Reinstall CUDA components
- Set GGML_VK_VISIBLE_DEVICES to control GPU visibility
- Fall back to CPU: set OLLAMA_NUM_GPU=0
