# Implementation Roadmap
## SmartInstall AI — Installation Agent & Log Collection Layer
**Version:** 1.0  
**Date:** 2026-06-01  
**Status:** Draft  

---

## Overview

The roadmap is structured into four sequential milestones, each building on the previous. Each milestone delivers a working, testable increment. No milestone requires AI, RAG, or LLM components.

```
Milestone 1          Milestone 2          Milestone 3          Milestone 4
Installation Agent → Log Collection   → Monitoring Framework → Consolidated Report
[Weeks 1–3]          [Weeks 4–6]          [Weeks 7–10]          [Weeks 11–13]
```

---

## Milestone 1 — Installation Agent

**Duration:** 3 weeks  
**Goal:** A working agent that can launch an EXE or MSI installer, track the session lifecycle, capture STDOUT/STDERR, and produce a minimal `session.json`.

---

### Tasks

#### M1-T01: Project Scaffold and Configuration
- Create solution structure per [Folder Structure Specification](folder-structure.md).
- Configure .NET 8 target framework; self-contained publish profile.
- Add `Microsoft.Extensions.DependencyInjection`, `Serilog`, `System.Text.Json` NuGet packages.
- Implement `ConfigProvider` loading `smartinstall.config.json` with schema validation.
- Implement `PrivilegeChecker` using `WindowsPrincipal` to validate Local Admin.
- Implement structured agent logging via Serilog (file sink + console sink).

**Dependency:** None  
**Estimated effort:** 3 days

---

#### M1-T02: Session Manager
- Implement `InstallationSession` model per Data Model Specification.
- Implement `SessionManager`: `CreateSession()`, `TransitionState()`, `FinalizeSession()`.
- State machine enforcement (valid transition table).
- Session working directory creation with correct ACL.
- `session.json` persistence (write on every state transition).
- `sessions_index.json` append-mode writer.
- Unit tests: state machine transitions, file write, recovery from partial state.

**Dependency:** M1-T01  
**Estimated effort:** 3 days

---

#### M1-T03: Installer Runner — EXE
- Implement `IInstallerRunner` for EXE type.
- `Process.Start()` with `ProcessStartInfo`; no `ShellExecute`; redirect STDOUT/STDERR.
- Async `OutputDataReceived` / `ErrorDataReceived` handlers with timestamped line buffering.
- Write `stdout.log` and `stderr.log` to session directory.
- Exit code capture; timeout enforcement with `Process.Kill()` on timeout.
- High-priority STDERR line detection (error/fail/exception keyword filter).
- Input validation: path traversal, extension whitelist, argument injection patterns.
- Credential redaction applied to command-line before any logging.
- Unit tests: mock process, timeout, exit code capture, STDOUT/STDERR limits.

**Dependency:** M1-T02  
**Estimated effort:** 4 days

---

#### M1-T04: Installer Runner — MSI
- Extend `IInstallerRunner` for MSI type.
- Construct `msiexec.exe` invocation with `/l*v` flag pointing to session directory.
- Exit code interpretation table (1603, 1618, 1619, etc.).
- Auto-detect if EXE invokes msiexec (child process detection, simplified for M1).
- Unit tests: argument construction, exit code table, log path generation.

**Dependency:** M1-T03  
**Estimated effort:** 2 days

---

#### M1-T05: CLI Entry Point
- Implement `Program.cs` CLI argument parser (using `System.CommandLine` or manual parsing).
- Map CLI flags to `StartSessionRequest`.
- Wire DI container: `IInstallationAgent`, `ISessionManager`, `IInstallerRunner`.
- Handle agent exit codes (0/1/2/3/4/5 per API Contracts §13).
- Integration test: end-to-end session start → installer runs → session end → `session.json` written.

**Dependency:** M1-T03, M1-T04  
**Estimated effort:** 2 days

---

#### M1-T06: EventBus
- Implement lightweight in-process pub/sub `EventBus`.
- Events: `SessionStarted`, `SessionEnded`, `InstallerLaunched`, `InstallerExited`, `CollectionComplete`.
- Synchronous dispatch (async in future phase).
- Unit tests: subscribe, publish, unsubscribe.

**Dependency:** M1-T01  
**Estimated effort:** 1 day

---

### Milestone 1 Acceptance Criteria

| ID | Criterion |
|----|-----------|
| M1-AC-01 | Agent launches `setup.exe` or `setup.msi` and captures exit code correctly. |
| M1-AC-02 | `session.json` written with all required metadata fields populated. |
| M1-AC-03 | `stdout.log` and `stderr.log` written with timestamped lines. |
| M1-AC-04 | Agent exits with correct process exit code (0/1/2/3/4/5). |
| M1-AC-05 | Session state machine enforces valid transitions; invalid transitions rejected. |
| M1-AC-06 | Credential patterns in command line are redacted before writing. |
| M1-AC-07 | Agent correctly detects and rejects invalid installer paths (traversal, wrong extension). |
| M1-AC-08 | Timeout is enforced: installer killed after configured duration; `TimedOut` recorded. |
| M1-AC-09 | Unit test coverage ≥ 80% for M1 components. |
| M1-AC-10 | Agent self-contained binary runs on clean Windows 10 machine without .NET pre-installed. |

---

## Milestone 2 — Log Collection

**Duration:** 3 weeks  
**Goal:** Implement all passive log collectors: Event Log, MSI verbose log, and WER. Each collector independently captures and serializes its artifacts to the session directory.

---

### Tasks

#### M2-T01: ICollector Base Interface and Result Framework
- Define `ICollector<TResult>` interface.
- Implement `CollectionResult<T>` with `Success`, `Failure`, `PartialSuccess` variants.
- Implement `CollectionError` model.
- Implement collector timeout wrapper (configurable per collector).
- Unit tests: partial failure, timeout enforcement.

**Dependency:** M1 complete  
**Estimated effort:** 1 day

---

#### M2-T02: Event Log Collector
- Implement `IEventCollector` using `System.Diagnostics.Eventing.Reader.EventLogReader`.
- Pre-snapshot: enumerate available channels; record `RecordId` watermarks.
- Post-snapshot: query entries since watermark using `EventLogQuery` with time filter.
- Serialize to `EventLogEntry[]`; write `event_log_delta.json`.
- Handle `UnauthorizedAccessException` per channel; skip with `CollectionError`.
- High-severity flagging (Level 1/2).
- Unit tests: mock `EventLogReader`, watermark logic, skip on access denied.

**Dependency:** M2-T01  
**Estimated effort:** 4 days

---

#### M2-T03: MSI Collector
- Implement `IMSICollector`.
- Pre-snapshot: generate log path; validate msiexec argument construction.
- Post-snapshot: check log exists; enforce 200 MB cap (truncate from beginning).
- Regex-based parser: extract `MSIError` (Return value 3, ERROR lines) and `MSIWarning` (Return value 2, WARN lines).
- Write `msi_errors.json`.
- Unit tests: parser with sample verbose log fixtures covering known error patterns; truncation behavior.

**Dependency:** M2-T01  
**Estimated effort:** 3 days

---

#### M2-T04: WER Collector
- Implement `IWERCollector`.
- Pre-snapshot: directory listing of both user and machine WER ReportQueue paths.
- Post-snapshot: identify new directories; 5-second post-exit delay before collection.
- `Report.wer` INI parser using `StreamReader` (no external INI library).
- Serialize to `CrashReport[]`; write `crash_reports.json`.
- Secondary crash detection via Event ID 1000/1001 (cross-reference with EventCollector results).
- Unit tests: mock WER directory with sample Report.wer; verify parsed fields; race condition handling.

**Dependency:** M2-T01, M2-T02  
**Estimated effort:** 3 days

---

#### M2-T05: Wire Collectors into Agent Lifecycle
- Integrate `EventCollector`, `MSICollector`, `WERCollector` into session lifecycle via DI.
- Pre-snapshot phase: parallel execution of all collectors' `TakePreSnapshot()`.
- Post-snapshot phase: parallel execution of `TakePostSnapshot()` for all collectors.
- Collector failures recorded as `CollectionError`; session continues.
- Integration tests: full session with real MSI package (test fixture MSI); verify all three artifact files written.

**Dependency:** M2-T02, M2-T03, M2-T04  
**Estimated effort:** 2 days

---

### Milestone 2 Acceptance Criteria

| ID | Criterion |
|----|-----------|
| M2-AC-01 | `event_log_delta.json` written after every session with correct entry count. |
| M2-AC-02 | Event log delta contains only entries after the pre-snapshot watermark. |
| M2-AC-03 | `msi_errors.json` populated for MSI installs containing known error patterns. |
| M2-AC-04 | `Return value 3` correctly detected and marked `isFatal=true`. |
| M2-AC-05 | WER crash report detected and parsed when test installer is intentionally crashed. |
| M2-AC-06 | Collector failure does not abort session; `collectionErrors` array populated in output. |
| M2-AC-07 | All collectors operate within defined timeout limits. |
| M2-AC-08 | MSI verbose log correctly truncated at 200 MB with `msiLogTruncated` flag set. |
| M2-AC-09 | Unit test coverage ≥ 80% for M2 components. |

---

## Milestone 3 — Monitoring Framework

**Duration:** 4 weeks  
**Goal:** Implement real-time monitoring collectors: Registry Monitor, Filesystem Monitor, and Process Monitor. These require active observation during the installation, not just before/after snapshots.

---

### Tasks

#### M3-T01: Registry Monitor
- Implement `IRegistryMonitor`.
- Recursive key/value enumeration using `Microsoft.Win32.Registry`.
- Streaming GZip-compressed JSON serialization (`registry_pre.json.gz`).
- Key count cap (100,000) with `RegistrySnapshotTruncated` flag.
- Post-snapshot structural diff algorithm (three-way: added/modified/deleted).
- High-risk key flagging (Run, Services, Winlogon paths).
- Sensitive value redaction before serialization.
- Run snapshot on `ThreadPriority.BelowNormal` background thread.
- Unit tests: diff algorithm with known before/after fixtures; truncation; redaction.

**Dependency:** M2-T01  
**Estimated effort:** 5 days

---

#### M3-T02: Filesystem Monitor
- Implement `IFilesystemMonitor`.
- Initialize `FileSystemWatcher` instances for each configured path.
- Set `InternalBufferSize = 65536`; enable `IncludeSubdirectories`.
- Handle `InternalBufferOverflow`: record lost event count.
- Event coalescing: 100ms window per path.
- Noise filter: configurable extension blocklist + temp path patterns.
- Event cap enforcement (10,000).
- High-risk path detection (System32, SysWOW64).
- Write `filesystem_events.json` on `StopWatching()`.
- Unit tests: mock watcher events; coalescing; cap; noise filter.

**Dependency:** M2-T01  
**Estimated effort:** 4 days

---

#### M3-T03: Process Monitor
- Implement `IProcessMonitor`.
- WMI `ManagementEventWatcher` subscription to `Win32_ProcessStartTrace` / `Win32_ProcessStopTrace`.
- PID-filtered WQL query to limit to installer process tree.
- Fallback polling mode (`Process.GetProcesses()` every 2 seconds) if WMI fails.
- Process tree builder (parent-child linkage; max depth 10).
- Resource sampler: `System.Diagnostics.Process.TotalProcessorTime` + `WorkingSet64` every 5 seconds.
- `ResourceSample` serialization.
- Write `process_tree.json` and `process_resource.json` on `StopTracking()`.
- Unit tests: tree builder with mock PIDs; WMI fallback; resource sample min/max/avg.

**Dependency:** M2-T01  
**Estimated effort:** 5 days

---

#### M3-T04: Integration of All Monitors into Session Lifecycle
- Wire `RegistryMonitor`, `FilesystemMonitor`, `ProcessMonitor` into `IInstallationAgent`.
- `StartWatching`/`StopWatching` calls at correct lifecycle points.
- Parallel post-snapshot execution for all six collectors.
- All collector `CollectionError`s aggregated.
- End-to-end integration tests: full session with all collectors active; verify all nine artifact files written.

**Dependency:** M3-T01, M3-T02, M3-T03  
**Estimated effort:** 3 days

---

#### M3-T05: Performance Validation
- Instrument agent with ETW/Stopwatch timing for each collection phase.
- Validate all NFR performance targets (§1 of non-functional spec) against real installation scenarios.
- Profile memory usage; resolve any leaks in long-running watcher threads.
- Document performance baseline results.

**Dependency:** M3-T04  
**Estimated effort:** 2 days

---

### Milestone 3 Acceptance Criteria

| ID | Criterion |
|----|-----------|
| M3-AC-01 | `registry_pre.json.gz` and `registry_delta.json` written for every session. |
| M3-AC-02 | Registry diff correctly identifies added/modified/deleted keys between pre/post snapshots. |
| M3-AC-03 | `filesystem_events.json` written; events attributed to monitored paths only. |
| M3-AC-04 | FileSystemWatcher buffer overflow handled gracefully (no agent crash; flag set). |
| M3-AC-05 | Process tree correctly reflects installer + child processes. |
| M3-AC-06 | WMI failure triggers automatic fallback to polling mode; no session abort. |
| M3-AC-07 | Agent CPU overhead ≤ 5% during active monitoring (validated with profiler). |
| M3-AC-08 | Agent memory ≤ 150 MB working set at steady state. |
| M3-AC-09 | All nine session artifact files present after a successful test install. |
| M3-AC-10 | Unit test coverage ≥ 80% for M3 components. |

---

## Milestone 4 — Consolidated Reporting

**Duration:** 3 weeks  
**Goal:** Implement the Log Collector aggregation layer, DiagnosticScore calculation, and finalize the consolidated report. Deliver a complete, validated JSON report usable by downstream pipelines.

---

### Tasks

#### M4-T01: Log Collector — Aggregation Engine
- Implement `ILogCollector.Aggregate()`.
- Assemble `ConsolidatedInstallationReport` from all collector results.
- Streaming `Utf8JsonWriter` serialization of `consolidated_report.json`.
- NDJSON writer for `consolidated_report.ndjson`.
- Report write retry logic (one retry on failure).
- `ReportWriteFailure` event on second failure.
- Unit tests: aggregation with all result types; streaming serialization; retry logic.

**Dependency:** M3-T04  
**Estimated effort:** 3 days

---

#### M4-T02: InstallationOutcome Computation
- Implement outcome decision logic:
  - `Success`: exitCode == 0 AND crashDetected == false AND msiErrors.fatalErrorDetected == false
  - `Crashed`: crashDetected == true
  - `Failure`: exitCode != 0 OR msiErrors.fatalErrorDetected == true
  - `Partial`: exitCode == 0 but collectionErrors present or incomplete data
  - `TimedOut`: session timed out
  - `Unknown`: outcome cannot be determined from available data
- Unit tests: all outcome branches with edge cases.

**Dependency:** M4-T01  
**Estimated effort:** 1 day

---

#### M4-T03: DiagnosticScore Heuristic
- Implement `DiagnosticScore` calculator (0–100):
  - Base: 0 (success)
  - +30 if `InstallationOutcome == Crashed`
  - +25 if `fatalMsiError == true`
  - +5 per `eventLogHighSeverityCount` (max +20)
  - +10 if `registryHighRiskChangeCount > 0`
  - +5 if `collectionErrors.Count > 0` (incomplete data penalty)
  - +5 if `filesystemHighRiskEventCount > 0`
  - Clamp to [0, 100]
- Document scoring formula in report schema.
- Unit tests: all weight combinations.

**Dependency:** M4-T02  
**Estimated effort:** 1 day

---

#### M4-T04: Report Schema Validation
- Implement `ConsolidatedInstallationReport` JSON Schema (draft-07).
- Write `report-schema.json` to `docs/schemas/`.
- Add schema validation step after report write using `JsonSchema.Net` or equivalent.
- Validation failure: log warning; do not fail session (report still preserved).
- Unit tests: valid report passes schema; known invalid reports caught.

**Dependency:** M4-T01  
**Estimated effort:** 2 days

---

#### M4-T05: Sessions Index Management
- Implement `sessions_index.json` append writer (thread-safe, append mode).
- Index entry: `{sessionId, startTimestamp, endTimestamp, outcome, diagnosticScore, reportPath}`.
- Implement `sessions_index` reader for future tooling (list all sessions, filter by outcome).
- Unit tests: concurrent append safety; index entry correctness.

**Dependency:** M4-T01  
**Estimated effort:** 1 day

---

#### M4-T06: End-to-End System Test Suite
- Define test matrix: EXE success, EXE failure, MSI success, MSI failure (1603), EXE crash, partial collector failure.
- Create test installer fixtures (simple NSIS/WiX MSI packages that succeed/fail/crash on demand).
- Automated tests: invoke agent → verify report schema → verify outcome → verify artifact files.
- Validate all M1–M4 acceptance criteria pass in the full integration test suite.

**Dependency:** All previous tasks  
**Estimated effort:** 4 days

---

#### M4-T07: Documentation and Deployment Packaging
- Generate XML doc comments → HTML documentation.
- Write deployment guide: prerequisites, AV exclusions, privilege requirements, configuration reference.
- Write `CLAUDE.md` with architecture summary for AI-assisted development in future phases.
- Package self-contained executable with default `smartinstall.config.json`.
- Create PowerShell install script for agent deployment.

**Dependency:** M4-T06  
**Estimated effort:** 2 days

---

### Milestone 4 Acceptance Criteria

| ID | Criterion |
|----|-----------|
| M4-AC-01 | `consolidated_report.json` written for all test scenarios; passes JSON schema validation. |
| M4-AC-02 | `InstallationOutcome` correct for all six test scenarios. |
| M4-AC-03 | `DiagnosticScore` non-zero for all failure/crash scenarios; 0–10 for clean installs. |
| M4-AC-04 | `sessions_index.json` updated correctly after every session. |
| M4-AC-05 | Report generation completes within 30 seconds of installer exit. |
| M4-AC-06 | NDJSON report file written and parseable line-by-line. |
| M4-AC-07 | All six integration test scenarios pass end-to-end. |
| M4-AC-08 | Self-contained executable runs on clean Windows 10 LTSC 2019 without .NET pre-installed. |
| M4-AC-09 | All Phase 1 NFR targets met (performance, security, reliability). |
| M4-AC-10 | Deployment guide reviewed and approved by stakeholder. |

---

## Milestone Dependencies Summary

```
M1 (Installation Agent)
    └── M2 (Log Collection) ─── depends on M1 complete
            └── M3 (Monitoring Framework) ─── depends on M2 complete
                    └── M4 (Consolidated Reporting) ─── depends on M3 complete
```

## Total Estimated Duration

| Milestone | Duration | Cumulative |
|-----------|----------|------------|
| M1 — Installation Agent | 3 weeks | Week 3 |
| M2 — Log Collection | 3 weeks | Week 6 |
| M3 — Monitoring Framework | 4 weeks | Week 10 |
| M4 — Consolidated Reporting | 3 weeks | Week 13 |

**Total Phase 1:** ~13 weeks (single developer; parallel tracks possible with 2 developers, targeting ~9 weeks)

---

## Future Phase Readiness Checklist

At the end of Phase 1, the following must be in place for Phase 2 (RAG / ChromaDB ingestion) readiness:

- [ ] `consolidated_report.json` schema documented and versioned (`schemaVersion: "1.0"`)
- [ ] All fields flat and machine-readable (no opaque blobs)
- [ ] `sessions_index.json` enables enumeration of all sessions for batch ingestion
- [ ] Session output directory structure consistent and documented
- [ ] `CollectionError` array present even when empty (ingestion pipeline does not need null checks)
- [ ] Agent internal logs written to `agent.log` in structured JSON format
- [ ] `CLAUDE.md` documents architecture for AI-assisted future development
