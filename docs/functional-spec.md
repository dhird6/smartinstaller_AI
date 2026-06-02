# Functional Specification
## SmartInstall AI — Installation Agent & Log Collection Layer
**Version:** 1.0  
**Date:** 2026-06-01  
**Status:** Draft  

---

## 1. Installation Session Management

### 1.1 Start Session

**Trigger:** User or automation invokes the Installation Agent with an installer path and optional metadata.

**Behavior:**
- Generate a globally unique `SessionId` (UUID v4).
- Record `StartTimestamp` (UTC, ISO 8601).
- Record machine context: hostname, OS version, OS build, architecture, logged-in user, domain.
- Accept and store caller-supplied metadata: `InstallerPath`, `InstallerType` (EXE/MSI), `ProductName`, `ProductVersion`, `CallerTag` (optional free-text label).
- Create session working directory: `<OutputRoot>\<SessionId>\`.
- Write session manifest file `session.json` to working directory.
- Take pre-installation snapshots (see §3, §5, §6).
- Emit `SessionStarted` event to internal event bus.

**Inputs:**
- `InstallerPath` (required): Absolute path to installer binary.
- `InstallerType` (optional): Auto-detected if omitted.
- `ProductName` (optional): Human-readable product label.
- `ProductVersion` (optional): Expected product version string.
- `CallerTag` (optional): Arbitrary label for correlation (e.g., JIRA ticket ID).
- `OutputDirectory` (optional): Override default output root.
- `AdditionalArgs` (optional): Arguments to pass to the installer.

**Outputs:**
- `SessionId`: UUID assigned to this session.
- Session working directory created.
- `session.json` manifest written.

**Error Conditions:**
- `InstallerPath` does not exist → abort with `INSTALLER_NOT_FOUND`.
- Insufficient disk space (< 1 GB free) → abort with `INSUFFICIENT_DISK_SPACE`.
- Output directory not writable → abort with `OUTPUT_DIR_NOT_WRITABLE`.
- Insufficient privileges → abort with `INSUFFICIENT_PRIVILEGES`.

---

### 1.2 End Session

**Trigger:** Installer process exits (normal or abnormal termination).

**Behavior:**
- Record `EndTimestamp` (UTC).
- Calculate `DurationSeconds`.
- Capture installer exit code.
- Take post-installation snapshots.
- Compute deltas (registry, event log, filesystem).
- Trigger log aggregation (§7).
- Write final `ConsolidatedInstallationReport` to session directory.
- Update `session.json` with final status and report path.
- Emit `SessionEnded` event.

**Error Conditions:**
- Snapshot failure → record partial data, mark field as `CollectionError`, continue.
- Report write failure → retry once; if still failing, emit `ReportWriteFailure` event with details.

---

### 1.3 Session Tracking

**Behavior:**
- Maintain an in-memory session registry mapping `SessionId` → `SessionState`.
- Session states: `Initializing` → `PreSnapshotting` → `Installing` → `PostSnapshotting` → `Aggregating` → `Completed` | `Failed`.
- Persist state transitions to `session.json` in real time (after each state change).
- Support graceful recovery: if agent crashes mid-session, partial artifacts are preserved and session is marked `Incomplete` on next startup.

---

### 1.4 Session Metadata

Captured automatically for every session:

| Field | Description |
|-------|-------------|
| `SessionId` | UUID v4 |
| `StartTimestamp` | UTC ISO 8601 |
| `EndTimestamp` | UTC ISO 8601 |
| `DurationSeconds` | Integer |
| `MachineName` | NetBIOS hostname |
| `OSVersion` | e.g., "Windows 10 Pro" |
| `OSBuild` | e.g., "19045.3693" |
| `Architecture` | x64 / x86 / ARM64 |
| `CurrentUser` | Domain\Username |
| `InstallerPath` | Absolute path |
| `InstallerType` | EXE / MSI |
| `ProductName` | Supplied or extracted |
| `ProductVersion` | Supplied or extracted |
| `CallerTag` | Optional label |
| `SessionStatus` | Final status enum |
| `ExitCode` | Installer exit code |
| `ReportPath` | Path to consolidated report |

---

## 2. Installer Execution

### 2.1 EXE Installation Monitoring

**Behavior:**
- Launch the EXE installer as a child process using `Process.Start()` with full argument passthrough.
- Set working directory to the installer's parent directory.
- Redirect `STDOUT` and `STDERR` streams asynchronously.
- Record PID of the spawned process.
- Monitor child process tree for spawned sub-processes.
- Capture exit code on process termination.
- Apply configurable timeout (default: 30 minutes); emit `InstallTimeout` if exceeded.

**Special handling:**
- Detect if EXE internally invokes `msiexec.exe` and automatically enable MSI log collection (§4).
- If EXE elevates via UAC, monitor the elevated process handle.

---

### 2.2 MSI Installation Monitoring

**Behavior:**
- Invoke `msiexec.exe` with the target MSI path and mandatory verbose logging flags:  
  `/i "<path>" /l*v "<session_dir>\msi_verbose.log" /qn /norestart`
- Append any caller-supplied MSI arguments.
- Redirect `STDOUT` and `STDERR`.
- Monitor `msiexec.exe` process and its child processes.
- Capture exit code.
- After process exit, parse the verbose log file (§4).

**Exit Code Interpretation:**

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1603 | Fatal error during installation |
| 1618 | Another installation already in progress |
| 1619 | Package could not be opened |
| 1620 | Package invalid |
| 1638 | Another version already installed |
| Other | Record raw value; flag as unknown |

---

### 2.3 Exit Code Capture

- Captured for both EXE and MSI installer types.
- Stored in `InstallerResult.ExitCode` (Int32).
- Mapped to `ExitCodeDescription` using a known-codes lookup table.
- Raw value always preserved regardless of mapping availability.

---

### 2.4 STDOUT Capture

- Captured via asynchronous `OutputDataReceived` event handler.
- Buffered line-by-line.
- Written to `<session_dir>\stdout.log`.
- Each line timestamped with UTC offset from session start.
- Maximum buffer: 50,000 lines; oldest lines rotated if exceeded.

---

### 2.5 STDERR Capture

- Captured via asynchronous `ErrorDataReceived` event handler.
- Buffered line-by-line.
- Written to `<session_dir>\stderr.log`.
- Each line timestamped.
- Lines containing keywords (`error`, `fail`, `exception`, `access denied`) flagged as `HighPriority`.

---

## 3. Event Log Collection

### 3.1 Pre-Installation Snapshot

**Behavior:**
- Before installer launch, enumerate entries from the following Windows Event Logs:
  - `Application`
  - `System`
  - `Setup`
  - `Microsoft-Windows-AppLocker/MSI and Script` (if available)
- Record the `RecordId` (sequence number) of the most recent entry in each log.
- Store as `PreSnapshot` baseline — this is a watermark, not a full copy.
- Timestamp the snapshot.

---

### 3.2 Post-Installation Snapshot

**Behavior:**
- After installer exit, enumerate all entries in the same logs with `RecordId` greater than the pre-snapshot watermark.
- Collect entries from the time window `[SessionStart - 30s, SessionEnd + 60s]` to capture async events.
- Serialize each qualifying entry to `EventLogEntry` data model.

---

### 3.3 Delta Detection

**Behavior:**
- Delta = all event log entries written after `PreSnapshot` watermark up to post-snapshot collection time.
- Filter out entries from processes unrelated to the installation (best effort, using PID correlation).
- Flag entries with Level `Error` (1) or `Critical` (2) as `HighSeverity`.
- Write delta to `<session_dir>\event_log_delta.json`.

---

## 4. MSI Log Collection

### 4.1 Verbose Logging

- MSI verbose log path: `<session_dir>\msi_verbose.log`.
- Captured for all MSI installations and for EXE installers that invoke msiexec.
- Raw log preserved in full regardless of size (up to 200 MB hard cap).

---

### 4.2 Error Extraction

**Behavior:**
- Parse verbose log for lines matching MSI error patterns:
  - Lines prefixed with `MSI (s)` containing `error` (case-insensitive)
  - Lines containing `Return value 3` (fatal action failure)
  - Lines containing `ERROR` in uppercase
  - Lines matching pattern `Property\(.*\)` with error-related property values
- Extract: line number, timestamp offset, raw text, action name if parseable.
- Write to `MSIError[]` collection in session report.

---

### 4.3 Warning Extraction

**Behavior:**
- Parse for lines matching warning patterns:
  - Lines containing `WARNING` or `WARN`
  - Lines with `Return value 2` (user cancelled or warning-level action result)
- Write to `MSIWarning[]` collection.

---

## 5. WER (Windows Error Reporting) Collection

### 5.1 Crash Detection

**Behavior:**
- Monitor `%LOCALAPPDATA%\Microsoft\Windows\WER\ReportQueue` and `%PROGRAMDATA%\Microsoft\Windows\WER\ReportQueue` for new directories created during the session window.
- Additionally watch the `Application` event log for Event ID 1000 (Application Error) and Event ID 1001 (Windows Error Reporting).
- If a crash is detected for a process in the monitored process tree, flag session with `CrashDetected = true`.

---

### 5.2 Crash Report Parsing

**Behavior:**
- For each new WER report directory created during session:
  - Read `Report.wer` (INI-style) for: `FriendlyEventName`, `AppName`, `AppVersion`, `ModName`, `ModVersion`, `Offset`, `ExceptionCode`.
  - Collect associated `.dmp` file path (do not copy dump; record path only unless `CopyDumps` option enabled).
  - Record `EventTime`, `ReportType`, `ConsentStatus`.
- Serialize to `CrashReport` data model.
- Link crash to `SessionId`.

---

## 6. File System Monitoring

### 6.1 File Creation

- Use `FileSystemWatcher` on installation-relevant directories:
  - `%ProgramFiles%`, `%ProgramFiles(x86)%`
  - `%CommonProgramFiles%`
  - `%SystemRoot%\System32`, `%SystemRoot%\SysWOW64`
  - `%APPDATA%`, `%LOCALAPPDATA%`
  - Custom paths specified in configuration
- Record: path, timestamp, file size, extension.
- Filter out OS-generated temp files matching known noise patterns (e.g., `~$*`, `*.tmp` in temp paths).

### 6.2 File Modification

- Capture `Changed` events from `FileSystemWatcher`.
- Record: path, timestamp, previous size if available.
- Limit capture to files modified within the monitored path scope.

### 6.3 File Deletion

- Capture `Deleted` events.
- Record: path, timestamp.
- Flag deletions in `System32` / `SysWOW64` as `HighRisk`.

**Performance limit:** Maximum 10,000 filesystem events per session; if exceeded, stop capturing and record `FileSystemEventCapCapReached = true`.

---

## 7. Registry Monitoring

### 7.1 Registry Snapshot

**Pre-installation snapshot targets:**

| Hive | Key Path |
|------|----------|
| HKLM | `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` |
| HKLM | `SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall` |
| HKCU | `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` |
| HKLM | `SYSTEM\CurrentControlSet\Services` |
| HKLM | `SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon` |
| HKLM | `SOFTWARE\Microsoft\Windows\CurrentVersion\Run` |
| HKCU | `SOFTWARE\Microsoft\Windows\CurrentVersion\Run` |

**Behavior:**
- Recursively enumerate all subkeys and values under each target path.
- Serialize to `RegistrySnapshot` object.
- Compress and write to `<session_dir>\registry_pre.json.gz`.

---

### 7.2 Registry Difference Detection

**Behavior:**
- Take identical post-installation snapshot.
- Compute diff:
  - **Added keys/values:** Present in post, absent in pre.
  - **Modified values:** Same path, different data.
  - **Deleted keys/values:** Present in pre, absent in post.
- Write `RegistryChange[]` to `<session_dir>\registry_delta.json`.
- Flag changes under `Run`, `Services`, and `Winlogon` as `HighRisk`.

---

## 8. Process Monitoring

### 8.1 Parent Process Detection

- Capture the full process context of the installer process at launch:
  - PID, PPID, process name, command line, start time, executable path, integrity level.
- Record agent's own PID for exclusion.

### 8.2 Child Process Detection

**Behavior:**
- Subscribe to WMI `Win32_ProcessStartTrace` and `Win32_ProcessStopTrace` events.
- Track all processes spawned as descendants of the installer PID.
- Build a process tree with parent-child relationships.
- For each process record: PID, PPID, name, command line, start time, end time, exit code.

### 8.3 Resource Usage Tracking

**Behavior:**
- Sample CPU% and working set (MB) for the installer process tree every 5 seconds.
- Record min, max, and average values.
- Flag sessions where peak CPU > 90% sustained for > 30 seconds.
- Flag sessions where peak memory > 2 GB.
- Write resource samples to `<session_dir>\process_resource.json`.

---

## 9. Log Aggregation

### 9.1 Consolidated Report Generation

**Trigger:** Called after all post-installation collection steps complete.

**Behavior:**
- Assemble `ConsolidatedInstallationReport` from all collected artifacts:
  - Session metadata
  - Installer result (exit code, stdout, stderr summary)
  - Event log delta (count + high-severity entries)
  - MSI errors and warnings
  - WER crash reports
  - Filesystem events (count + high-risk entries)
  - Registry changes (count + high-risk changes)
  - Process tree
  - Resource usage summary
- Write to `<session_dir>\consolidated_report.json` (pretty-printed).
- Write machine-readable version to `<session_dir>\consolidated_report.ndjson` (one JSON object per line for streaming ingestion).
- Compute `InstallationOutcome`: `Success` | `Failure` | `Partial` | `Crashed` | `Unknown` based on exit code + crash detection + MSI error presence.
- Calculate `DiagnosticScore` (0–100): a heuristic severity score based on counts of errors, high-severity events, registry high-risk changes, and crash presence.
- Write report index entry to `<OutputRoot>\sessions_index.json` (append-mode).
