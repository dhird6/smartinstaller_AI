# Data Model Specification
## SmartInstall AI — Installation Agent & Log Collection Layer
**Version:** 1.0  
**Date:** 2026-06-01  
**Status:** Draft  

---

## Conventions

- All timestamps: UTC, ISO 8601 format (`yyyy-MM-ddTHH:mm:ss.fffZ`)
- All paths: Absolute Windows paths, backslash-separated
- `Required`: Field must be present and non-null
- `Optional`: Field may be null or omitted
- All string fields: Max length noted where applicable
- Enums serialized as strings

---

## 1. InstallationSession

Top-level session tracking object. Written to `session.json`.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `sessionId` | `string` (UUID v4) | Yes | Format: `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$` | Unique session identifier |
| `schemaVersion` | `string` | Yes | e.g., `"1.0"` | Schema version for forward compatibility |
| `startTimestamp` | `string` | Yes | ISO 8601 UTC | Session start time |
| `endTimestamp` | `string` | No | ISO 8601 UTC | Session end time; null while in progress |
| `durationSeconds` | `number` | No | ≥ 0 | Calculated on session end |
| `sessionStatus` | `SessionStatus` enum | Yes | See enum | Current session state |
| `machineName` | `string` | Yes | Max 255 chars | NetBIOS hostname |
| `osVersion` | `string` | Yes | Max 100 chars | e.g., "Windows 10 Pro" |
| `osBuild` | `string` | Yes | Max 50 chars | e.g., "19045.3693" |
| `architecture` | `string` | Yes | `x64` \| `x86` \| `ARM64` | System architecture |
| `currentUser` | `string` | Yes | Max 255 chars | `DOMAIN\Username` |
| `installerPath` | `string` | Yes | Valid absolute path | Path to installer binary |
| `installerType` | `InstallerType` enum | Yes | See enum | EXE or MSI |
| `productName` | `string` | No | Max 255 chars | Human-readable product name |
| `productVersion` | `string` | No | Max 100 chars | Expected/detected product version |
| `callerTag` | `string` | No | Max 500 chars | Arbitrary correlation label |
| `outputDirectory` | `string` | Yes | Valid absolute path | Session working directory |
| `exitCode` | `integer` | No | Int32 | Installer exit code; null if timed out |
| `installationOutcome` | `InstallationOutcome` enum | No | See enum | Computed on aggregation |
| `diagnosticScore` | `integer` | No | 0–100 | Severity heuristic score |
| `reportPath` | `string` | No | Valid absolute path | Path to consolidated report |
| `agentVersion` | `string` | Yes | SemVer | SmartInstall AI agent version |

**SessionStatus enum:** `Initializing` | `PreSnapshotting` | `Installing` | `PostSnapshotting` | `Aggregating` | `Completed` | `Failed` | `Incomplete` | `TimedOut`

**InstallerType enum:** `EXE` | `MSI` | `Unknown`

**InstallationOutcome enum:** `Success` | `Failure` | `Partial` | `Crashed` | `TimedOut` | `Unknown`

---

## 2. InstallerResult

Captures the direct output of the installer process execution.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `sessionId` | `string` (UUID) | Yes | References InstallationSession | Parent session |
| `exitCode` | `integer` | Yes | Int32 | Raw installer exit code |
| `exitCodeDescription` | `string` | No | Max 255 chars | Human-readable mapping of exit code |
| `isKnownExitCode` | `boolean` | Yes | | Whether exit code is in known-codes table |
| `installerPid` | `integer` | Yes | > 0 | PID of the installer process |
| `commandLine` | `string` | Yes | Max 32,767 chars | Full command line (sensitive args redacted) |
| `startTimestamp` | `string` | Yes | ISO 8601 UTC | Process start time |
| `endTimestamp` | `string` | No | ISO 8601 UTC | Process end time |
| `timedOut` | `boolean` | Yes | | True if killed due to timeout |
| `stdoutPath` | `string` | No | Valid path | Path to captured stdout log file |
| `stderrPath` | `string` | No | Valid path | Path to captured stderr log file |
| `stdoutLineCount` | `integer` | No | ≥ 0 | Total lines captured |
| `stderrLineCount` | `integer` | No | ≥ 0 | Total lines captured |
| `stderrHighPriorityCount` | `integer` | No | ≥ 0 | Lines flagged as high-priority |

---

## 3. EventLogEntry

Represents a single Windows Event Log entry captured in the delta.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `recordId` | `integer` | Yes | > 0 | Event log record sequence number |
| `logName` | `string` | Yes | Max 255 chars | e.g., "Application", "System" |
| `source` | `string` | Yes | Max 255 chars | Event provider/source name |
| `eventId` | `integer` | Yes | 0–65535 | Windows Event ID |
| `level` | `EventLevel` enum | Yes | See enum | Severity level |
| `timestamp` | `string` | Yes | ISO 8601 UTC | Event timestamp |
| `message` | `string` | No | Max 32,767 chars | Formatted event message |
| `processId` | `integer` | No | > 0 | Originating process PID |
| `threadId` | `integer` | No | > 0 | Originating thread ID |
| `machineName` | `string` | No | Max 255 chars | Source machine |
| `isHighSeverity` | `boolean` | Yes | | True if Level is Error or Critical |
| `sessionId` | `string` (UUID) | Yes | | Parent session reference |

**EventLevel enum:** `Critical` (1) | `Error` (2) | `Warning` (3) | `Information` (4) | `Verbose` (5) | `Unknown` (0)

---

## 4. MSIError

Represents a single error entry extracted from an MSI verbose log.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `sessionId` | `string` (UUID) | Yes | | Parent session reference |
| `lineNumber` | `integer` | Yes | > 0 | Line number in verbose log |
| `rawText` | `string` | Yes | Max 4,096 chars | Raw log line text |
| `actionName` | `string` | No | Max 255 chars | MSI action name if parseable |
| `errorCode` | `string` | No | Max 50 chars | Extracted error code if present |
| `isFatal` | `boolean` | Yes | | True if "Return value 3" pattern matched |
| `timestampOffset` | `number` | No | ≥ 0 | Seconds from MSI log start |

---

## 5. MSIWarning

Represents a single warning entry extracted from an MSI verbose log.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `sessionId` | `string` (UUID) | Yes | | Parent session reference |
| `lineNumber` | `integer` | Yes | > 0 | Line number in verbose log |
| `rawText` | `string` | Yes | Max 4,096 chars | Raw log line text |
| `actionName` | `string` | No | Max 255 chars | MSI action name if parseable |
| `isCancelled` | `boolean` | Yes | | True if "Return value 2" pattern matched |
| `timestampOffset` | `number` | No | ≥ 0 | Seconds from MSI log start |

---

## 6. CrashReport

Represents a WER crash report detected during the session.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `sessionId` | `string` (UUID) | Yes | | Parent session reference |
| `reportDirectory` | `string` | Yes | Valid path | WER report folder path |
| `appName` | `string` | No | Max 255 chars | Crashing application name |
| `appVersion` | `string` | No | Max 100 chars | Application version |
| `moduleName` | `string` | No | Max 255 chars | Faulting module name |
| `moduleVersion` | `string` | No | Max 100 chars | Faulting module version |
| `exceptionCode` | `string` | No | Max 20 chars | e.g., "0xC0000005" |
| `offset` | `string` | No | Max 20 chars | Fault offset in module |
| `eventTime` | `string` | No | ISO 8601 UTC | Crash event time |
| `reportType` | `string` | No | Max 100 chars | WER report type |
| `consentStatus` | `string` | No | Max 100 chars | WER consent status |
| `dumpFilePath` | `string` | No | Valid path or null | Dump file path (recorded only) |
| `friendlyEventName` | `string` | No | Max 255 chars | WER friendly event name |
| `isInInstallerTree` | `boolean` | Yes | | True if crash process is in installer process tree |

---

## 7. FileSystemEvent

Represents a single filesystem change event captured during installation.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `sessionId` | `string` (UUID) | Yes | | Parent session reference |
| `eventType` | `FSEventType` enum | Yes | See enum | Type of filesystem change |
| `filePath` | `string` | Yes | Max 32,767 chars | Absolute path of affected file/dir |
| `extension` | `string` | No | Max 20 chars | File extension (lowercase) |
| `timestamp` | `string` | Yes | ISO 8601 UTC | Event timestamp |
| `fileSizeBytes` | `integer` | No | ≥ 0 | File size at time of event (Created/Changed) |
| `isDirectory` | `boolean` | Yes | | True if path is a directory |
| `isHighRisk` | `boolean` | Yes | | True if path is in System32/SysWOW64 |
| `sessionOffsetMs` | `integer` | No | ≥ 0 | Milliseconds from session start |

**FSEventType enum:** `Created` | `Modified` | `Deleted` | `Renamed`

---

## 8. RegistryChange

Represents a single registry change detected between pre- and post-install snapshots.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `sessionId` | `string` (UUID) | Yes | | Parent session reference |
| `changeType` | `RegistryChangeType` enum | Yes | See enum | Type of change |
| `hive` | `string` | Yes | `HKLM` \| `HKCU` \| `HKCR` \| `HKU` | Registry hive |
| `keyPath` | `string` | Yes | Max 16,383 chars | Full key path (excluding hive) |
| `valueName` | `string` | No | Max 16,383 chars | Value name; null for key-level changes |
| `valueType` | `string` | No | Max 50 chars | e.g., `REG_SZ`, `REG_DWORD` |
| `previousData` | `string` | No | Max 4,096 chars | Previous value data (Modified only); sensitive values redacted |
| `newData` | `string` | No | Max 4,096 chars | New value data; sensitive values redacted |
| `isHighRisk` | `boolean` | Yes | | True if key is in Run, Services, or Winlogon |

**RegistryChangeType enum:** `KeyAdded` | `KeyDeleted` | `ValueAdded` | `ValueModified` | `ValueDeleted`

---

## 9. ProcessInfo

Represents a single process in the installer process tree.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `sessionId` | `string` (UUID) | Yes | | Parent session reference |
| `pid` | `integer` | Yes | > 0 | Process ID |
| `parentPid` | `integer` | No | > 0 | Parent process ID |
| `processName` | `string` | Yes | Max 255 chars | Process executable name |
| `executablePath` | `string` | No | Max 32,767 chars | Full path to executable |
| `commandLine` | `string` | No | Max 32,767 chars | Command line (sensitive args redacted) |
| `startTimestamp` | `string` | Yes | ISO 8601 UTC | Process start time |
| `endTimestamp` | `string` | No | ISO 8601 UTC | Process end time; null if still running |
| `exitCode` | `integer` | No | Int32 | Process exit code |
| `integrityLevel` | `string` | No | Max 50 chars | e.g., "High", "Medium", "System" |
| `treeDepth` | `integer` | Yes | 0–10 | Depth from installer root (root = 0) |
| `isInstallerRoot` | `boolean` | Yes | | True if this is the directly-launched installer |

---

## 10. ResourceSample

Represents a single CPU/memory sample for the installer process tree.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `sessionId` | `string` (UUID) | Yes | | Parent session reference |
| `sampleTimestamp` | `string` | Yes | ISO 8601 UTC | Sample time |
| `sessionOffsetSeconds` | `number` | Yes | ≥ 0 | Seconds from session start |
| `totalCpuPercent` | `number` | Yes | 0–100 | Aggregate CPU% across monitored process tree |
| `totalWorkingSetMb` | `number` | Yes | ≥ 0 | Total working set in MB |
| `processCount` | `integer` | Yes | ≥ 1 | Number of processes sampled |

---

## 11. ConsolidatedInstallationReport

Top-level report object. Written to `consolidated_report.json`.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `schemaVersion` | `string` | Yes | e.g., `"1.0"` | Report schema version |
| `reportGeneratedAt` | `string` | Yes | ISO 8601 UTC | Report generation timestamp |
| `session` | `InstallationSession` | Yes | | Full session record |
| `installerResult` | `InstallerResult` | Yes | | Installer execution result |
| `eventLogDelta` | `EventLogEntry[]` | Yes | | Array of event log entries |
| `eventLogDeltaCount` | `integer` | Yes | ≥ 0 | Total entries captured |
| `eventLogHighSeverityCount` | `integer` | Yes | ≥ 0 | Count of Error/Critical entries |
| `msiErrors` | `MSIError[]` | Yes | | Empty array if no MSI log |
| `msiWarnings` | `MSIWarning[]` | Yes | | Empty array if no MSI log |
| `crashReports` | `CrashReport[]` | Yes | | Empty array if no crashes detected |
| `crashDetected` | `boolean` | Yes | | True if any crash detected |
| `filesystemEvents` | `FileSystemEvent[]` | Yes | | Array of FS events |
| `filesystemEventCount` | `integer` | Yes | ≥ 0 | Total FS events captured |
| `filesystemEventCapReached` | `boolean` | Yes | | True if 10,000 cap was hit |
| `registryChanges` | `RegistryChange[]` | Yes | | Array of registry changes |
| `registryChangeCount` | `integer` | Yes | ≥ 0 | Total registry changes detected |
| `processTree` | `ProcessInfo[]` | Yes | | All processes in installer tree |
| `resourceSamples` | `ResourceSample[]` | Yes | | All resource samples |
| `resourcePeakCpuPercent` | `number` | No | 0–100 | Peak CPU% across session |
| `resourcePeakMemoryMb` | `number` | No | ≥ 0 | Peak working set in MB |
| `collectionErrors` | `CollectionError[]` | Yes | | Errors during collection (non-fatal) |
| `installationOutcome` | `InstallationOutcome` enum | Yes | | Computed outcome |
| `diagnosticScore` | `integer` | Yes | 0–100 | Heuristic severity score |

---

## 12. CollectionError

Records a non-fatal error that occurred during collection.

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `sessionId` | `string` (UUID) | Yes | | Parent session reference |
| `collectorName` | `string` | Yes | Max 100 chars | Name of the failing collector |
| `errorCode` | `string` | Yes | Max 50 chars | Internal error code |
| `message` | `string` | Yes | Max 2,000 chars | Error description |
| `timestamp` | `string` | Yes | ISO 8601 UTC | When the error occurred |
| `isPartialData` | `boolean` | Yes | | True if partial data was still collected |
