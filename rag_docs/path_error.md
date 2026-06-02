# Error: ollama not recognized

## Symptoms
- 'ollama' is not recognized as an internal or external command

## Root Causes
- Ollama not installed
- PATH variable missing
- Terminal opened before PATH update
- Installation incomplete

## Diagnosis
- Run: where ollama
- Check: C:\Users\<user>\AppData\Local\Programs\Ollama
- Verify ollama.exe exists

## Resolution
- Add Ollama folder to PATH
- Restart terminal
- Reinstall Ollama if executable missing
