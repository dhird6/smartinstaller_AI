# Category: AUTOCAD_GPU_DRIVER_FAILURE

## Error Signature
- OpenGL initialization failed
- DirectX error
- Unsupported GPU
- Hardware acceleration unavailable
- Graphics driver incompatible

## Meaning
Autodesk product (AutoCAD, Revit, etc.) failed to initialize due to unsupported GPU, outdated drivers, or missing DirectX/OpenGL components.

## Common Causes
- GPU driver version below Autodesk minimum requirement
- Integrated GPU used instead of dedicated GPU
- DirectX version mismatch
- OpenGL not supported on current driver
- GPU blacklisted by Autodesk hardware certification

## Recommended Actions
- Update GPU drivers to latest certified version for your Autodesk product
- Check Autodesk Certified Hardware list for GPU compatibility
- Force dedicated GPU: NVIDIA Control Panel → Manage 3D Settings → Program Settings
- Disable hardware acceleration as temporary workaround in AutoCAD options
- Install latest DirectX redistributable from Microsoft

## Verification Commands
- dxdiag
- nvidia-smi (NVIDIA)
- wmic path win32_VideoController get name,driverversion

## Confidence Scoring
- High: OpenGL, DirectX, or GPU driver error in logs
- Medium: AutoCAD launches but crashes on 3D viewport or drawing open
