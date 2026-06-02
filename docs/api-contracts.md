# API Contract Specification
## SmartInstall AI — Installation Agent & Log Collection Layer
**Version:** 1.0  
**Date:** 2026-06-01  
**Status:** Draft  

---

## Conventions

- All interfaces defined in C# style for implementation clarity.
- Method signatures represent both public CLI and internal module boundaries.
- `Result<T>` pattern used throughout: every operation returns a result wrapper rather than throwing.
- Error codes follow the pattern `<COMPONENT>_<CONDITION>` (e.g., `SESSION_INSTALLER_NOT_FOUND`).

---

## 1. IInstallationAgent — Top-Level Entry Point

The primary interface for callers (CLI, automation scripts, future SDK).

```
Interface: IInstallationAgent
```

### 1.1 StartSession

```
Input:
  StartSessionRequest {
    installerPath:     string    [Required] Absolute path to installer binary
    installerType:     string?   [Optional] "EXE" | "MSI" | auto-detected
    productName:       string?   [Optional] Max 255 chars
    productVersion:    string?   [Optional] Max 100 chars
    callerTag:         string?   [Optional] Max 500 chars
    outputDirectory:   string?   [Optional] Override default output root
    additionalArgs:    string?   [Optional] Arguments forwarded to installer
    timeoutSeconds:    integer?  [Optional] Default: 1800 (30 min)
    copyDumps:         boolean?  [Optional] Default: false
  }

Output:
  StartSessionResponse {
    success:           boolean
    sessionId:         string?   UUID v4; null on failure
    sessionDirectory:  string?   Absolute path to session output dir
    error:             ApiError? Non-null on failure
  }

Error Codes:
  SESSION_INSTALLER_NOT_FOUND       InstallerPath does not exist
  SESSION_INSUFFICIENT_DISK_SPACE   < 1 GB free on output drive
  SESSION_OUTPUT_DIR_NOT_WRITABLE   Cannot create or write to output directory
  SESSION_INSUFFICIENT_PRIVILEGES   Required Windows privileges not held
  SESSION_ALREADY_ACTIVE            A session is already in progress (Phase 1)
  SESSION_INVALID_INPUT             Input validation failure (path traversal, etc.)
```

### 1.2 WaitForCompletion

```
Input:
  WaitRequest {
    sessionId:        string    [Required] UUID of active session
    pollIntervalMs:   integer?  [Optional] Default: 1000ms
  }

Output:
  WaitResponse {
    success:          boolean
    sessionId:        string
    outcome:          string    InstallationOutcome enum value
    exitCode:         integer?
    reportPath:       string?   Path to consolidated_report.json
    durationSeconds:  number?
    error:            ApiError?
  }

Error Codes:
  SESSION_NOT_FOUND                 SessionId does not exist
  SESSION_WAIT_TIMEOUT              Internal wait mechanism timed out
```

### 1.3 GetSessionStatus

```
Input:
  string sessionId   [Required]

Output:
  SessionStatusResponse {
    sessionId:        string
    status:           string    SessionStatus enum value
    startTimestamp:   string?
    endTimestamp:     string?
    currentPhase:     string?   Human-readable current activity
    error:            ApiError?
  }

Error Codes:
  SESSION_NOT_FOUND
```

### 1.4 GetReport

```
Input:
  GetReportRequest {
    sessionId:    string    [Required]
    format:       string?   "json" | "ndjson"; default "json"
  }

Output:
  GetReportResponse {
    success:      boolean
    sessionId:    string
    reportPath:   string?   Absolute path to report file
    format:       string
    error:        ApiError?
  }

Error Codes:
  SESSION_NOT_FOUND
  SESSION_REPORT_NOT_READY      Session has not completed yet
  SESSION_REPORT_WRITE_FAILED   Report exists but could not be read back
```

---

## 2. ISessionManager — Internal Interface

```
Interface: ISessionManager
```

### 2.1 CreateSession

```
Input:  StartSessionRequest (see §1.1)
Output: Result<InstallationSession>
  Success: populated InstallationSession with SessionId and Initializing status
  Failure: error code + message

Side Effects:
  - Creates session working directory
  - Writes initial session.json
  - Emits SessionStarted event to EventBus
```

### 2.2 TransitionState

```
Input:
  sessionId:      string    [Required]
  targetState:    SessionStatus enum
  metadata:       Dictionary<string, object>?  Optional additional fields to merge into session.json

Output: Result<bool>

Validation:
  Only valid state transitions permitted (see state machine below)
  Invalid transition → SESSION_INVALID_STATE_TRANSITION

State Machine:
  Initializing → PreSnapshotting
  PreSnapshotting → Installing
  Installing → PostSnapshotting
  PostSnapshotting → Aggregating
  Aggregating → Completed
  Any state → Failed (on unrecoverable error)
  Any state → TimedOut (on timeout)
```

### 2.3 FinalizeSession

```
Input:
  sessionId:     string
  exitCode:      integer?
  outcome:       InstallationOutcome enum
  reportPath:    string?

Output: Result<InstallationSession>

Side Effects:
  - Writes final session.json
  - Appends entry to sessions_index.json
  - Emits SessionEnded event to EventBus
```

---

## 3. IInstallerRunner — Internal Interface

```
Interface: IInstallerRunner
```

### 3.1 Launch

```
Input:
  InstallerRunRequest {
    installerPath:    string
    installerType:    InstallerType enum
    arguments:        string?
    sessionDirectory: string
    timeoutSeconds:   integer
  }

Output:
  InstallerRunResult {
    pid:              integer
    startTimestamp:   string   ISO 8601 UTC
    exitCode:         integer?  null if not yet exited
    timedOut:         boolean
    stdoutPath:       string?
    stderrPath:       string?
    error:            ApiError?
  }

Error Codes:
  RUNNER_LAUNCH_FAILED            Process.Start() threw
  RUNNER_ACCESS_DENIED            Cannot launch installer (ACL/AV block)
  RUNNER_INVALID_INSTALLER_TYPE   Type not supported
```

### 3.2 WaitForExit

```
Input:
  pid:              integer
  timeoutSeconds:   integer

Output:
  ProcessExitResult {
    exitCode:         integer
    endTimestamp:     string
    timedOut:         boolean
  }
```

---

## 4. ICollector — Base Interface for All Collectors

```
Interface: ICollector<TResult>
```

All collector modules implement this generic interface.

```
Properties:
  Name:         string    Collector identifier (e.g., "EventLogCollector")
  IsEnabled:    bool      Configurable via smartinstall.config.json

Methods:

  TakePreSnapshot(sessionId: string) → Result<Unit>
    Called before installer launches.
    Captures baseline state.
    Must complete within CollectorPreSnapshotTimeoutSeconds (default: 30s).
    On timeout: returns error, does not throw.

  TakePostSnapshot(sessionId: string) → Result<TResult>
    Called after installer exits.
    Captures post-install state.
    Computes delta where applicable.
    Must complete within CollectorPostSnapshotTimeoutSeconds (default: 60s).

  GetResult(sessionId: string) → Result<TResult>
    Returns collected data for inclusion in ConsolidatedReport.
    May be called any time after TakePostSnapshot completes.

Error Codes (all collectors):
  COLLECTOR_DISABLED              IsEnabled = false
  COLLECTOR_PRE_SNAPSHOT_TIMEOUT  Pre-snapshot exceeded timeout
  COLLECTOR_POST_SNAPSHOT_TIMEOUT Post-snapshot exceeded timeout
  COLLECTOR_ACCESS_DENIED         Insufficient privilege to access data source
  COLLECTOR_DATA_SOURCE_ERROR     Underlying API error (wrapped with details)
```

---

## 5. IEventCollector

```
Extends: ICollector<EventLogDeltaResult>

TakePreSnapshot:
  Input:  sessionId: string
  Output: Result<Unit>
  Side Effect: Records RecordId watermarks for Application, System, Setup, AppLocker logs

TakePostSnapshot:
  Input:  sessionId: string
  Output: Result<EventLogDeltaResult>
    EventLogDeltaResult {
      entries:              EventLogEntry[]
      totalEntryCount:      integer
      highSeverityCount:    integer
      logsScanned:          string[]   Names of logs successfully scanned
      logsSkipped:          string[]   Names of logs that failed/were inaccessible
    }

Error Codes:
  EVENTLOG_CHANNEL_UNAVAILABLE    Specific log channel not accessible
  EVENTLOG_RECORD_ID_OVERFLOW     RecordId wrapped around (very long running session)
```

---

## 6. IMSICollector

```
Extends: ICollector<MSICollectionResult>

TakePreSnapshot:
  Input:  sessionId: string
  Output: Result<Unit>
  Side Effect: Records expected verbose log path; ensures msiexec args include /l*v

GetMsiLogPath(sessionId: string) → string
  Returns the expected verbose log file path for the session.
  Used by InstallerRunner to construct msiexec arguments.

TakePostSnapshot:
  Input:  sessionId: string
  Output: Result<MSICollectionResult>
    MSICollectionResult {
      verboseLogPath:     string?
      verboseLogSizeBytes: integer
      errors:             MSIError[]
      warnings:           MSIWarning[]
      errorCount:         integer
      warningCount:       integer
      fatalErrorDetected: boolean
    }

Error Codes:
  MSI_LOG_NOT_FOUND               Verbose log file was not created
  MSI_LOG_TOO_LARGE               Log exceeds 200 MB cap (truncated, partial parse)
  MSI_PARSE_ERROR                 Log file could not be parsed
```

---

## 7. IWERCollector

```
Extends: ICollector<WERCollectionResult>

TakePreSnapshot:
  Input:  sessionId: string
  Output: Result<Unit>
  Side Effect: Snapshots existing WER report directories

TakePostSnapshot:
  Input:  sessionId: string
  Output: Result<WERCollectionResult>
    WERCollectionResult {
      crashDetected:    boolean
      crashReports:     CrashReport[]
      reportCount:      integer
    }

Error Codes:
  WER_DIR_ACCESS_DENIED           Cannot read WER report queue directory
  WER_REPORT_PARSE_ERROR          Report.wer file could not be parsed
```

---

## 8. IRegistryMonitor

```
Extends: ICollector<RegistryDeltaResult>

TakePreSnapshot:
  Input:  sessionId: string
  Output: Result<Unit>
  Side Effect: Writes registry_pre.json.gz

TakePostSnapshot:
  Input:  sessionId: string
  Output: Result<RegistryDeltaResult>
    RegistryDeltaResult {
      changes:              RegistryChange[]
      totalChangeCount:     integer
      highRiskChangeCount:  integer
      keysScanned:          integer
      valuesScanned:        integer
    }

Error Codes:
  REGISTRY_KEY_ACCESS_DENIED      Specific key requires elevated ACL
  REGISTRY_SNAPSHOT_TOO_LARGE     Snapshot exceeds memory/disk limits
```

---

## 9. IFilesystemMonitor

```
Extends: ICollector<FilesystemEventResult>

StartWatching(sessionId: string) → Result<Unit>
  Initializes FileSystemWatcher instances on all configured paths.
  Called at session start.

StopWatching(sessionId: string) → Result<FilesystemEventResult>
  Stops all watchers and flushes buffered events.
  FilesystemEventResult {
    events:              FileSystemEvent[]
    totalEventCount:     integer
    capReached:          boolean
    highRiskEventCount:  integer
    watcherErrors:       string[]   Paths where watcher failed to initialize
  }

Error Codes:
  FS_WATCHER_PATH_NOT_FOUND       Monitored path does not exist
  FS_WATCHER_ACCESS_DENIED        Cannot watch path
  FS_BUFFER_OVERFLOW              Internal OS buffer overflowed; events lost
```

---

## 10. IProcessMonitor

```
Extends: ICollector<ProcessMonitorResult>

StartTracking(sessionId: string, rootPid: integer) → Result<Unit>
  Begins WMI process event subscription rooted at rootPid.

StopTracking(sessionId: string) → Result<ProcessMonitorResult>
  Unsubscribes WMI watchers and finalizes data.
  ProcessMonitorResult {
    processTree:          ProcessInfo[]
    resourceSamples:      ResourceSample[]
    peakCpuPercent:       number
    peakMemoryMb:         number
    totalProcessCount:    integer
  }

Error Codes:
  PROCESS_WMI_SUBSCRIPTION_FAILED WMI event subscription could not be established
  PROCESS_ROOT_PID_NOT_FOUND      Installer PID not found (already exited before tracking started)
```

---

## 11. ILogCollector

```
Interface: ILogCollector
```

### 11.1 Aggregate

```
Input:
  AggregationRequest {
    sessionId:              string
    installerResult:        InstallerResult
    eventLogResult:         EventLogDeltaResult
    msiResult:              MSICollectionResult
    werResult:              WERCollectionResult
    registryResult:         RegistryDeltaResult
    filesystemResult:       FilesystemEventResult
    processResult:          ProcessMonitorResult
    collectionErrors:       CollectionError[]
  }

Output:
  Result<AggregationResponse> {
    reportPath:             string   Absolute path to consolidated_report.json
    ndjsonPath:             string   Absolute path to consolidated_report.ndjson
    installationOutcome:    InstallationOutcome enum
    diagnosticScore:        integer  0–100
  }

Error Codes:
  AGGREGATION_WRITE_FAILED        Could not write report to disk (retry once)
  AGGREGATION_SERIALIZATION_ERROR JSON serialization failed
```

---

## 12. ApiError — Common Error Response

```
ApiError {
  errorCode:      string    Internal error code (e.g., "SESSION_INSTALLER_NOT_FOUND")
  message:        string    Human-readable description
  detail:         string?   Additional context (e.g., inner exception message)
  timestamp:      string    ISO 8601 UTC when error occurred
  component:      string    Component name that raised the error
}
```

---

## 13. CLI Entry Point Contract

The agent is invoked from the command line as follows:

```
smartinstall.exe [OPTIONS] <installer-path>

Arguments:
  <installer-path>          Required. Absolute path to installer.

Options:
  --type <EXE|MSI>          Optional. Override installer type detection.
  --product-name <name>     Optional. Product name label.
  --product-version <ver>   Optional. Product version label.
  --tag <label>             Optional. Caller correlation tag.
  --output-dir <path>       Optional. Override output root directory.
  --args <"...">            Optional. Arguments forwarded to installer (quoted).
  --timeout <seconds>       Optional. Installer timeout. Default: 1800.
  --copy-dumps              Optional. Copy WER dump files to session dir. Default: false.
  --log-level <level>       Optional. Agent log level: Verbose|Debug|Info|Warning|Error. Default: Info.
  --no-fs-monitor           Optional. Disable filesystem monitoring.
  --no-registry-monitor     Optional. Disable registry monitoring.

Exit Codes (agent process):
  0    Session completed; installation succeeded (installer exit code 0)
  1    Session completed; installation failed (non-zero installer exit code)
  2    Session completed; crash detected
  3    Agent error (could not complete monitoring — see agent.log)
  4    Invalid arguments
  5    Insufficient privileges
```
