# Error Handling Specifications

## Principles

1. **User-friendly messages** in chat — technical details in logs
2. **No silent failures** — always provide feedback
3. **Graceful degradation** — missing assets/config should not crash UI
4. **No secret exposure** in error messages or logs

## UI Error Categories

### Unknown Chat Command

- **Trigger**: Unrecognized user input
- **Response**: Chat assistant message with supported command hints
- **Recovery**: User retries with valid command

### Installer Not Found

- **Trigger**: `install <name>` where file doesn't exist
- **Response**: Chat error message listing available installers
- **Recovery**: User corrects filename or uses `list`

### Installation Failure

- **Trigger**: Orchestrator detects failure outcome
- **Response**:
  - Monitoring page: error visualization
  - Chat: install summary with failure details
  - Troubleshooting: expandable error cards
  - Optional: SLM diagnosis if enabled

### SLM / Ollama Unavailable

- **Trigger**: Ollama not running or model missing
- **Response**: Chat system message indicating AI unavailable
- **Recovery**: User starts Ollama; installation data still available without AI

### Worker Busy

- **Trigger**: User submits command while install in progress
- **Response**: Input disabled, typing indicator shown
- **Recovery**: Automatic re-enable on completion

## Asset Fallbacks

| Missing Asset | Fallback |
|---------------|----------|
| Company logo | Bundled `cctech_logo.svg` |
| App logo | Bundled `app_logo.svg` → company logo |
| Invalid image | Empty transparent pixmap |

## Logging

- Agent logs to `logs/` directory
- Log levels: INFO for workflow steps, ERROR for failures
- Never log: passwords, tokens, full registry values with PII

## Exception Handling in Workers

- Workers catch exceptions and emit error callbacks
- Controller converts to chat system messages
- UI thread never receives unhandled exceptions from workers

## Configuration Errors

- Invalid config: Pydantic validation error at startup
- Missing directories: auto-created via `ensure_project_layout`
- Invalid paths: resolved relative to project root

## Display Guidelines

- Error text color: `palette.error` (#ef4444) for critical states
- System messages: centered pill format in chat
- Troubleshooting cards: expandable with severity indicators
