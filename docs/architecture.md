# System Architecture Specification
## SmartInstall AI — Installation Agent & Log Collection Layer
**Version:** 1.0  
**Date:** 2026-06-01  
**Status:** Draft  

---

## 1. High-Level Architecture

SmartInstall AI Phase 1 is a single-machine, in-process agent composed of a coordination core and a set of independent collector modules. All components run within the same Windows process under elevated privileges.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SmartInstall AI Agent                          │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      Installation Agent Core                      │  │
│  │   SessionManager │ InstallerRunner │ EventBus │ ConfigProvider   │  │
│  └──────────────────────────────┬───────────────────────────────────┘  │
│                                 │ orchestrates                          │
│            ┌────────────────────┼────────────────────┐                 │
│            ▼                    ▼                    ▼                 │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐       │
│  │  Event Collector  │ │   MSI Collector  │ │   WER Collector  │       │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘       │
│            ▼                    ▼                    ▼                 │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐       │
│  │  Registry Monitor │ │  FS Monitor      │ │ Process Monitor  │       │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘       │
│                                 │                                       │
│                                 ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        Log Collector                              │  │
│  │           (Aggregates all collector outputs → Report)            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                 │                                       │
│                                 ▼                                       │
│                    ┌────────────────────────┐                          │
│                    │   Output File System    │                          │
│                    │  <SessionDir>/*.json   │                          │
│                    └────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘

External Dependencies (Windows OS):
  Windows Event Log API │ WMI (Win32_Process*) │ Registry API
  FileSystemWatcher     │ WER Report Directories │ msiexec.exe
```

---

## 2. Component Diagram Description

### 2.1 Installation Agent Core

The central orchestrator. Owns the session lifecycle.

**Sub-components:**

| Sub-component | Responsibility |
|---------------|---------------|
| `SessionManager` | Creates and tracks `InstallationSession` objects; transitions state machine; writes `session.json` |
| `InstallerRunner` | Launches EXE or MSI installer processes; captures STDOUT/STDERR; monitors PID; fires start/end events |
| `EventBus` | In-process publish/subscribe bus; decouples session events from collector reactions |
| `ConfigProvider` | Loads and validates `smartinstall.config.json`; supplies config objects to all components |
| `PrivilegeChecker` | Validates required Windows privileges at startup; aborts with clear error if insufficient |

---

### 2.2 Event Collector

Interfaces with the Windows Event Log API.

**Responsibilities:**
- Establish watermark at session start across target event log channels.
- Collect new entries after installer exits using `EventLogReader` / `EvtQuery` Win32 API.
- Serialize entries to `EventLogEntry` model.
- Write `event_log_delta.json` to session directory.

**Windows API surface:** `System.Diagnostics.Eventing.Reader.EventLogReader`, native `EvtQuery`

---

### 2.3 MSI Collector

Interfaces with MSI verbose log files produced by msiexec.

**Responsibilities:**
- Ensure verbose log flag is passed to msiexec invocations.
- Watch for log file creation.
- After install, parse raw log using regex-based parser.
- Extract `MSIError` and `MSIWarning` entries.
- Write parsed results to session report.

**Windows API surface:** File I/O (log file parsing only)

---

### 2.4 WER Collector

Monitors Windows Error Reporting infrastructure.

**Responsibilities:**
- Take directory listing snapshot of WER report queue paths at session start.
- Watch for new WER report directories during session.
- Parse `Report.wer` files using INI parser.
- Record crash metadata; link to session.
- Write `CrashReport[]` to session report.

**Windows API surface:** `FileSystemWatcher` on WER directories, `EventLog` for Event IDs 1000/1001

---

### 2.5 Registry Monitor

Takes before/after registry snapshots and computes diff.

**Responsibilities:**
- Recursively read defined registry hive paths using `Microsoft.Win32.Registry`.
- Serialize to compressed JSON snapshot.
- After install, re-read and compute structural diff (added/modified/deleted keys and values).
- Write `RegistryChange[]` to session report.

**Windows API surface:** `Microsoft.Win32.Registry`, `Microsoft.Win32.RegistryKey`

---

### 2.6 File System Monitor

Uses `FileSystemWatcher` to track installation-attributable filesystem changes.

**Responsibilities:**
- Initialize watchers on configured monitored directories before install starts.
- Buffer `Created`, `Changed`, `Deleted` events with timestamps.
- Apply noise filters.
- Enforce event cap.
- Flush buffered events to `FileSystemEvent[]` in session report.

**Windows API surface:** `System.IO.FileSystemWatcher`

---

### 2.7 Process Monitor

Tracks the installer process tree and resource usage.

**Responsibilities:**
- Subscribe to WMI `Win32_ProcessStartTrace` and `Win32_ProcessStopTrace`.
- Build and maintain process tree rooted at installer PID.
- Sample CPU and memory every 5 seconds via `System.Diagnostics.Process`.
- On session end, serialize `ProcessInfo[]` tree and resource sample array.

**Windows API surface:** `System.Management.ManagementEventWatcher` (WMI), `System.Diagnostics.Process`

---

### 2.8 Log Collector

Final aggregation stage.

**Responsibilities:**
- Receive completed collector outputs via event bus or direct injection.
- Merge all artifacts into `ConsolidatedInstallationReport`.
- Compute `InstallationOutcome` and `DiagnosticScore`.
- Serialize report to JSON and NDJSON.
- Update global `sessions_index.json`.

---

## 3. Data Flow Description

```
[Caller] ──invoke──▶ [SessionManager.StartSession()]
                            │
                            ├──▶ [PrivilegeChecker] (validate)
                            ├──▶ [ConfigProvider] (load config)
                            ├──▶ [EventCollector.TakePreSnapshot()]
                            ├──▶ [RegistryMonitor.TakePreSnapshot()]
                            ├──▶ [WERCollector.TakePreSnapshot()]
                            ├──▶ [FilesystemMonitor.StartWatching()]
                            ├──▶ [ProcessMonitor.StartTracking()]
                            └──▶ [InstallerRunner.Launch()]
                                        │
                              [Installer runs ...]
                                        │
                                        ├── STDOUT/STDERR ──▶ [InstallerRunner buffer]
                                        ├── Process events ──▶ [ProcessMonitor]
                                        ├── FS events ──────▶ [FilesystemMonitor]
                                        └── [Installer Exits]
                                                │
                            [SessionManager.EndSession()]
                                        │
                            ├──▶ [EventCollector.TakePostSnapshot() + ComputeDelta()]
                            ├──▶ [RegistryMonitor.TakePostSnapshot() + ComputeDelta()]
                            ├──▶ [WERCollector.CollectNewReports()]
                            ├──▶ [MSICollector.ParseVerboseLog()]
                            ├──▶ [ProcessMonitor.StopTracking() + Serialize()]
                            ├──▶ [FilesystemMonitor.StopWatching() + Flush()]
                            └──▶ [LogCollector.Aggregate() ──▶ ConsolidatedReport]
                                                                        │
                                                        ┌───────────────┴────────────────┐
                                                        ▼                                ▼
                                              consolidated_report.json     sessions_index.json (append)
```

---

## 4. Module Responsibilities Summary

| Module | Owns | Reads | Writes |
|--------|------|-------|--------|
| SessionManager | Session lifecycle, state machine | Config, caller input | `session.json` |
| InstallerRunner | Process launch, STDOUT/STDERR | Installer binary | `stdout.log`, `stderr.log` |
| EventCollector | Event log delta | Windows Event Log API | `event_log_delta.json` |
| MSICollector | MSI log parsing | `msi_verbose.log` | `msi_errors.json` |
| WERCollector | WER report detection | WER directories, Event Log | `crash_reports.json` |
| RegistryMonitor | Registry diff | Windows Registry | `registry_pre.json.gz`, `registry_delta.json` |
| FilesystemMonitor | FS event capture | FileSystemWatcher | `filesystem_events.json` |
| ProcessMonitor | Process tree + resources | WMI, Process API | `process_tree.json`, `process_resource.json` |
| LogCollector | Report assembly | All collector outputs | `consolidated_report.json`, `sessions_index.json` |

---

## 5. Integration Boundaries

### 5.1 Internal Boundaries

- All collector modules implement `ICollector` interface.
- Collectors communicate results only via `CollectionResult<T>` return types — no shared mutable state.
- `EventBus` is the only cross-module communication channel for lifecycle events.
- Session working directory is the only shared I/O surface between modules.

### 5.2 External Boundaries

| External System | Integration Method | Direction | Notes |
|-----------------|-------------------|-----------|-------|
| Windows Event Log | `EventLogReader` (.NET) | Read | Requires `SeSecurityPrivilege` for Security log |
| Windows Registry | `Microsoft.Win32.Registry` | Read | Key enumeration only; no writes |
| WMI | `ManagementEventWatcher` | Read | Async event subscription |
| FileSystem | `FileSystemWatcher` | Read | Requires path access rights |
| WER Directories | `FileSystemWatcher` + direct read | Read | `%PROGRAMDATA%\...\WER` may need Admin rights |
| msiexec.exe | Process launch with args | Write (flags) | Passes `/l*v` flag; no binary modification |
| Caller Process | CLI / API invocation | Input | Receives installer path + options |

### 5.3 Future Phase Integration Boundaries (Design-Time Consideration)

| Future System | Recommended Integration Point |
|---------------|-------------------------------|
| ChromaDB (Phase 2) | Consumes `consolidated_report.json` via file watcher or ingestion CLI |
| Ollama / SLM (Phase 3) | Reads ingested vector store; does not require agent modification |
| Web Dashboard (Phase 4) | Reads `sessions_index.json` + individual session directories |
| CI/CD Pipeline | Invokes agent via CLI; reads exit code + JSON report |

---

## 6. Deployment Architecture

```
Target Windows Machine
│
├── C:\ProgramData\SmartInstallAI\
│   ├── smartinstall.config.json         ← Configuration
│   ├── agent.log                        ← Agent internal log
│   └── sessions\
│       └── <SessionId>\                 ← Per-session artifacts
│           ├── session.json
│           ├── stdout.log
│           ├── stderr.log
│           ├── msi_verbose.log
│           ├── event_log_delta.json
│           ├── registry_pre.json.gz
│           ├── registry_delta.json
│           ├── filesystem_events.json
│           ├── crash_reports.json
│           ├── process_tree.json
│           ├── process_resource.json
│           └── consolidated_report.json
│
└── sessions_index.json                  ← Global session index
```
