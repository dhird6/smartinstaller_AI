# Non-Functional Requirements Specification
## SmartInstall AI — Installation Agent & Log Collection Layer
**Version:** 1.0  
**Date:** 2026-06-01  
**Status:** Draft  

---

## 1. Performance Requirements

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|--------------------|
| PERF-01 | Agent startup time (from invocation to pre-snapshot complete) | ≤ 5 seconds | Stopwatch from process start to `SessionStarted` event |
| PERF-02 | CPU overhead during active monitoring | ≤ 5% of one logical core (average over session duration) | ETW performance counter sampling |
| PERF-03 | Memory footprint of agent process | ≤ 150 MB working set at steady state | Task Manager / Process Explorer |
| PERF-04 | Registry snapshot (full pre/post) duration | ≤ 10 seconds per snapshot | Internal timing instrumentation |
| PERF-05 | Event log delta collection duration | ≤ 3 seconds | Internal timing instrumentation |
| PERF-06 | Consolidated report generation time | ≤ 30 seconds after installer exits | Measured from `SessionEnded` trigger to report write complete |
| PERF-07 | FileSystemWatcher event processing latency | ≤ 500 ms per event (buffered) | Internal queue depth monitoring |
| PERF-08 | WMI process event subscription latency | ≤ 1 second from process spawn to capture | Validated in test harness |
| PERF-09 | Disk I/O write throughput for log artifacts | ≤ 50 MB/s peak write during collection | Performance counters |
| PERF-10 | JSON serialization of consolidated report | ≤ 5 seconds for reports up to 10 MB | Internal timing |

---

## 2. Scalability Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| SCAL-01 | Maximum session artifact size per install | ≤ 500 MB (soft), ≤ 1 GB (hard cap with truncation) |
| SCAL-02 | Maximum filesystem events captured | 10,000 events per session; cap enforced with flag |
| SCAL-03 | Maximum event log entries in delta | 50,000 entries; oldest truncated if exceeded |
| SCAL-04 | Maximum MSI verbose log size retained | 200 MB hard cap; truncated from oldest lines |
| SCAL-05 | Maximum stdout/stderr lines retained | 50,000 lines per stream |
| SCAL-06 | Maximum process tree depth tracked | 10 levels deep |
| SCAL-07 | Sessions index file | Supports up to 100,000 session entries before compaction needed |
| SCAL-08 | Concurrent sessions (Phase 1) | 1 (sequential); architecture must not preclude future parallel sessions |

**Future scalability considerations (Phase 2+):**
- Agent architecture must allow horizontal scale via a queue-based collector model.
- JSON output schema must be forward-compatible; new fields added as optional.
- Collector modules must be loadable/unloadable without restarting the agent.

---

## 3. Security Requirements

| ID | Requirement | Detail |
|----|-------------|--------|
| SEC-01 | Minimum privilege principle | Agent requests only the Windows privileges necessary: `SeDebugPrivilege` (process inspection), `SeSecurityPrivilege` (event log access). No blanket SYSTEM escalation. |
| SEC-02 | No privilege escalation bypass | Agent must not bypass UAC, disable Windows Defender, or alter security policies. |
| SEC-03 | Installer binary integrity | Agent must not modify, patch, inject into, or wrap installer binaries in any way. |
| SEC-04 | Output directory ACL | Session output directory ACL'd to agent-running user + Local Administrators only; world-readable directories are not permitted. |
| SEC-05 | No credential capture | Agent must never log process command-line arguments containing passwords or tokens (filter patterns: `/password:`, `/pwd:`, `-pw`, `--token`). |
| SEC-06 | Crash dump handling | Agent records dump file paths but does not copy or transmit dump files by default. `CopyDumps` option disabled by default; requires explicit opt-in. |
| SEC-07 | No network transmission | Phase 1 agent must not transmit any collected data over the network. All output is local disk only. |
| SEC-08 | Input validation | All caller-supplied inputs (paths, tags, args) sanitized to prevent path traversal and injection. |
| SEC-09 | WMI query safety | WMI queries use parameterized or schema-validated queries; no string-concatenated WQL. |
| SEC-10 | Log data sensitivity | Captured registry values and environment variables must redact known sensitive value patterns (passwords, API keys matching common regex patterns). |

---

## 4. Reliability Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| REL-01 | Partial failure tolerance | Any single collector failure must not abort the session; partial data is collected and failure is recorded. |
| REL-02 | Agent crash recovery | On agent restart after crash, existing session directories are preserved and marked `Incomplete`; no data is deleted. |
| REL-03 | Session atomicity | `session.json` written after each state transition to ensure consistent state on recovery. |
| REL-04 | Report write reliability | Consolidated report write retried once on failure; failure recorded in session manifest. |
| REL-05 | Installer process isolation | If the monitored installer kills the agent (edge case), session artifacts written so far are preserved on disk. |
| REL-06 | Timeout handling | All long-running operations (snapshot, WMI queries, report generation) have configurable timeouts; expired operations are logged and skipped rather than hanging. |
| REL-07 | Event log access | If an event log channel is inaccessible, log the access error and continue with available channels. |
| REL-08 | FileSystemWatcher buffer overflow | `InternalBufferOverflow` handled: log count of lost events, continue monitoring. |

---

## 5. Maintainability Requirements

| ID | Requirement | Detail |
|----|-------------|--------|
| MAINT-01 | Code modularity | Each collector (Event Log, MSI, WER, Registry, Filesystem, Process) must be an independent, swappable module implementing a defined interface. |
| MAINT-02 | Configuration-driven behavior | All tunable parameters (timeouts, caps, monitored paths, registry keys) externalized to a single configuration file (`smartinstall.config.json`). No magic numbers in code. |
| MAINT-03 | Structured logging | Agent internal logs use structured JSON (via Serilog or equivalent), written to `<OutputRoot>\agent.log`. Log level configurable (Verbose / Debug / Info / Warning / Error). |
| MAINT-04 | Unit testability | All collector modules must be testable without a live Windows installation; abstractions over Win32/WMI/Registry APIs required. |
| MAINT-05 | Dependency injection | Core services (process runner, filesystem watcher, registry reader, WMI client) injected via DI container for testability. |
| MAINT-06 | Documentation | All public interfaces documented with XML doc comments; generated HTML documentation required. |
| MAINT-07 | Versioned schema | JSON output schema versioned with `schemaVersion` field; breaking changes increment major version. |

---

## 6. Extensibility Requirements

| ID | Requirement | Detail |
|----|-------------|--------|
| EXT-01 | Collector plugin model | New collectors (e.g., ETW trace collector, network monitor) must be addable without modifying existing collector code. |
| EXT-02 | Report format plugins | Report serializers (JSON, XML, CSV) pluggable without modifying aggregation logic. |
| EXT-03 | AI pipeline readiness | Consolidated report schema designed so that every field can be directly embedded into a vector store without transformation; no nested opaque blobs. |
| EXT-04 | Event bus | Internal `SessionStarted` / `SessionEnded` / `CollectionComplete` events published to an in-process event bus; future phases subscribe without modifying agent core. |
| EXT-05 | Configuration schema versioned | `smartinstall.config.json` includes `configVersion`; migration helpers must be provided for schema upgrades. |
| EXT-06 | ChromaDB / RAG readiness | Output directory structure and report format designed to be directly consumable by a future ingestion pipeline (Phase 2) with no reformatting. |
| EXT-07 | Multi-installer type extensibility | `IInstallerRunner` interface must allow new installer type handlers (AppX, MSIX, Inno Setup, NSIS) to be added without modifying session management. |
