# Architecture Specifications

## Package Structure

```
smartinstall/
├── agent/          # Backend domain
├── core/           # Shared models
└── ui/             # Presentation layer
```

## Dependency Rules

- `ui/` MAY import from `agent/` and `core/`
- `agent/` MAY import from `core/` only
- `core/` SHALL NOT import from `ui/` or `agent/`
- `ui/services/` SHALL NOT import Qt widgets

## Key Classes

| Class | Layer | Responsibility |
|-------|-------|----------------|
| `MainShell` | UI Shell | Root window, page routing, chat reparenting |
| `DesktopController` | UI Controller | Command handling, worker lifecycle |
| `FloatingChatWidget` | UI Shell | Overlay chat container |
| `FullChatPage` | UI Page | Full-page chat workspace |
| `ChatPanel` | UI Widget | Message display and input |
| `AutomatedRunOrchestrator` | Agent | Installation workflow |
| `SmartInstallConfig` | Agent | Configuration model |

## Communication Patterns

### Signals (Qt)
- User input: `ChatPanel.message_submitted` → `MainShell` → `DesktopController`
- Status: `EventBus` → `QtEventBridge.status_update` → UI updates

### Callbacks
- `controller.on_message` — chat message delivery
- `controller.on_run_completed` — installation finished
- `controller.on_slm_completed` — diagnosis finished

## Threading Model

| Worker | Thread | Task |
|--------|--------|------|
| `InstallWorkflowWorker` | QThread | Run orchestrator |
| `SlmDiagnosisWorker` | QThread | Ollama RAG call |

UI updates ONLY via signals/callbacks from workers — never direct widget access from threads.

## Configuration Architecture

```
smartinstall.config.json
        ↓
SmartInstallConfig (Pydantic)
        ↓
build_container() → DI container
        ↓
DesktopController / Orchestrator
```

## Asset Resolution

```
assets/images/ → company_logo_path() / app_logo_path()
        ↓ (fallback)
project root logo files
        ↓ (fallback)
bundled ui/resources/icons/
```

## Extension Points

- New page: add to `MainShell._stack` + sidebar indices
- New chat command: extend `DesktopController.handle_user_input`
- New collector: register in agent orchestration
- New theme token: extend `CCTechPalette`
