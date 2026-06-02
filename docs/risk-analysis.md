# Risk Analysis
## SmartInstall AI — Installation Agent & Log Collection Layer
**Version:** 1.0  
**Date:** 2026-06-01  
**Status:** Draft  

---

## Risk Rating Matrix

| Likelihood | Impact | Rating |
|-----------|--------|--------|
| High | High | Critical |
| High | Medium | High |
| Medium | High | High |
| Medium | Medium | Medium |
| Low | High | Medium |
| Low | Medium | Low |
| Any | Low | Low |

---

## 1. Technical Risks

### RISK-T-01 — WMI Event Subscription Reliability
**Rating:** High  
**Description:** `Win32_ProcessStartTrace` and `Win32_ProcessStopTrace` WMI events are known to miss events under high process-creation load, or fail entirely if the WMI service (`winmgmt`) is in a degraded state. Short-lived child processes may exit before WMI delivers the start event.

**Impact:** Incomplete process tree; child processes not captured; resource samples missing.

**Mitigation:**
1. Supplement WMI with periodic `Process.GetProcesses()` polling (every 2 seconds) to catch processes WMI missed.
2. At session end, enumerate all processes with PPID in the tracked tree to fill gaps.
3. If WMI subscription fails at startup, fall back entirely to polling mode and record `WMI_UNAVAILABLE` in `CollectionError`.
4. Detect WMI service health at startup; emit warning if degraded.

---

### RISK-T-02 — FileSystemWatcher Internal Buffer Overflow
**Rating:** High**  
**Description:** `FileSystemWatcher` uses a 4 KB–64 KB internal OS buffer. High-velocity file operations (e.g., extracting thousands of files from an archive) can overflow this buffer, causing lost events. The `InternalBufferOverflow` event fires but lost events cannot be recovered.

**Impact:** Incomplete filesystem event log; missed file creations.

**Mitigation:**
1. Set `InternalBufferSize` to maximum (65536 bytes) for all watchers.
2. Handle `InternalBufferOverflow`: record count of lost events; continue monitoring.
3. Set `NotifyFilter` to minimum required flags only (`FileName | DirectoryName | LastWrite`) to reduce event volume.
4. Apply noise filters early to prevent buffer flooding from temp file churn.
5. Document known limitation in report: `filesystemEventCapReached` and `bufferOverflowOccurred` flags.

---

### RISK-T-03 — Registry Snapshot Memory Pressure
**Rating:** Medium  
**Description:** A full recursive snapshot of `HKLM\SOFTWARE` and `HKCU\SOFTWARE` can enumerate millions of values on machines with heavy software installs, consuming significant memory and time.

**Impact:** Agent OOM; snapshot timeout; incomplete baseline.

**Mitigation:**
1. Snapshot only the defined key paths (not all of SOFTWARE); do not enumerate outside defined scope.
2. Enforce per-snapshot time limit (10 seconds); abort with partial data if exceeded.
3. Stream-write snapshot to compressed JSON (GZip) rather than materializing full object in memory.
4. Impose a maximum key count per snapshot (100,000 keys); truncate and record `RegistrySnapshotTruncated = true`.

---

### RISK-T-04 — Async WER Report Write Race Condition
**Rating:** Medium  
**Description:** Windows writes WER reports asynchronously after a crash. The agent may complete its post-snapshot collection before WER has finished writing the `Report.wer` file, resulting in a missed or incomplete crash report.

**Impact:** Crash not detected; crash report incomplete.

**Mitigation:**
1. After installer exits with a non-zero code or suspected crash, insert a configurable delay (default: 5 seconds) before WER collection.
2. Watch WER directory using `FileSystemWatcher` during the entire session; collect any new reports appearing within 60 seconds of installer exit.
3. Cross-reference with Event ID 1000/1001 in Application log as a secondary crash signal.

---

### RISK-T-05 — MSI Verbose Log Truncation
**Rating:** Medium  
**Description:** For large or complex MSI packages, the verbose log may reach the 200 MB hard cap before installation completes. Truncating from the beginning may remove critical early-phase context.

**Impact:** Missing MSI action sequence context; error lines may be present but referenced actions absent.

**Mitigation:**
1. Truncate from the beginning, not the end (preserve most recent lines where errors appear).
2. Record `msiLogTruncated = true` in session report with bytes discarded.
3. Always extract errors and warnings before truncation check; error extraction is not affected.

---

### RISK-T-06 — .NET Runtime Version Mismatch
**Rating:** Medium  
**Description:** Target machines may have an older .NET runtime or no .NET installed at all.

**Impact:** Agent fails to launch; no monitoring possible.

**Mitigation:**
1. Publish agent as self-contained single-file executable (no external .NET dependency).
2. Include runtime version check at startup; emit clear error if minimum version not met (even for self-contained, for diagnostic clarity).
3. Test on Windows 10 LTSC 2019 specifically.

---

## 2. Windows Compatibility Risks

### RISK-W-01 — Windows 10 LTSC vs SAC Feature Divergence
**Rating:** Medium  
**Description:** Windows 10 LTSC 2019 (build 17763) lacks some Event Log channels and WMI classes present in later SAC builds. AppLocker/MSIX event channels may be absent.

**Impact:** Certain event log channels unavailable; partial collection.

**Mitigation:**
1. All event log channel access wrapped in try/catch with per-channel fallback.
2. Collect list of available channels at startup; skip unavailable channels gracefully.
3. Test matrix must include LTSC 2019, LTSC 2021, Win10 21H2, Win11 22H2, Server 2019, Server 2022.

---

### RISK-W-02 — WMI Namespace Differences Between OS Versions
**Rating:** Low  
**Description:** `Win32_ProcessStartTrace` availability and behavior differs between Windows 10 and Windows Server. Some Server editions require specific WMI service configuration.

**Impact:** Process tracking falls back to polling.

**Mitigation:**
1. Check WMI namespace availability at startup; fall back to polling if subscription fails.
2. Log fallback mode clearly.

---

### RISK-W-03 — Long Path Support Not Enabled
**Rating:** Low  
**Description:** Windows long-path support (paths > 260 chars) requires a Group Policy or registry flag. Installer-created files with long paths may generate `PathTooLongException` in the filesystem monitor.

**Impact:** Filesystem events for long-path files silently dropped.

**Mitigation:**
1. Enable long-path support in the agent's application manifest (`<longPathAware>true</longPathAware>`).
2. Catch `PathTooLongException` in FS event handlers; record path hash and truncated path.
3. Document requirement for Windows Group Policy long-path enablement in deployment guide.

---

### RISK-W-04 — Antivirus / EDR Interference
**Rating:** High  
**Description:** Endpoint security products (Defender, CrowdStrike, Carbon Black, etc.) may:
- Block agent from reading process command lines
- Delay or block installer launch
- Interfere with WMI subscriptions
- Quarantine agent binary

**Impact:** Incomplete data collection; agent blocked entirely.

**Mitigation:**
1. Document agent binary hash and signing requirement; sign with trusted code-signing certificate.
2. Provide AV exclusion guidance for `<OutputRoot>` and agent binary path.
3. Detect `UnauthorizedAccessException` from process command-line reads; record as `CollectionError` and continue.
4. Test agent on machines with Defender ATP enabled.

---

## 3. Privilege Escalation Risks

### RISK-P-01 — Privilege Misuse by Malicious Caller
**Rating:** High  
**Description:** The agent runs with elevated privileges. A malicious caller could pass a crafted `InstallerPath` or `AdditionalArgs` to execute arbitrary code with the agent's privilege level.

**Impact:** Privilege escalation; system compromise.

**Mitigation:**
1. Validate `InstallerPath` against path traversal patterns (`..`, `//`, null bytes, UNC paths) before use.
2. Validate `AdditionalArgs` against injection patterns (`;`, `&`, `|`, command chaining sequences).
3. Whitelist allowed installer file extensions (`.exe`, `.msi`); reject others.
4. Never construct shell command strings; use `ProcessStartInfo` with explicit `Arguments` property (not `ShellExecute`).
5. Run under a dedicated service account rather than SYSTEM where possible.

---

### RISK-P-02 — Session Directory Tampering
**Rating:** Medium  
**Description:** A low-privilege process could modify or inject data into the session output directory if ACLs are not correctly set.

**Impact:** Falsified diagnostic reports; potential escalation via crafted JSON consumed by future pipeline.

**Mitigation:**
1. Set session directory ACL at creation: owner = agent user, full control; SYSTEM full control; no other users.
2. Validate report JSON schema before writing to `sessions_index.json`.
3. Future ingestion pipeline must validate report schema and source integrity before processing.

---

### RISK-P-03 — Credential Leakage via Command-Line Logging
**Rating:** High  
**Description:** Installers may receive credentials via command-line arguments (e.g., `/password:Secret123`). Capturing the full command line risks logging sensitive credentials.

**Impact:** Credential exposure in log files.

**Mitigation:**
1. Apply redaction filter to all captured command-line strings before writing to disk.
2. Redaction patterns: `/password:*`, `/pwd:*`, `-pw *`, `--token *`, `--key *`, `--secret *` (configurable list).
3. Replace matched segments with `[REDACTED]`.
4. Redaction applied before any disk write; never stored in memory beyond processing step.

---

## 4. Log Access Risks

### RISK-L-01 — Security Event Log Access Denied
**Rating:** Low  
**Description:** The Security event log requires `SeSecurityPrivilege`. If not granted, the agent cannot read it.

**Impact:** Missing security events potentially relevant to installation (e.g., privilege use, object access).

**Mitigation:**
1. Security log is not in the default monitored channels for Phase 1 (avoids the privilege requirement).
2. Document as a known limitation; flag in report if Security log was skipped.
3. Future phase: add opt-in `--include-security-log` flag requiring explicit privilege grant.

---

### RISK-L-02 — MSI Verbose Log Write Race (Multi-User)
**Rating:** Low  
**Description:** If multiple users run `msiexec` simultaneously (Terminal Server scenarios), the verbose log path collision could cause log data mix-up.

**Impact:** MSI log contaminated with data from another session.

**Mitigation:**
1. Log path includes `SessionId` to guarantee uniqueness.
2. Phase 1 explicitly does not support concurrent sessions; document limitation.

---

## 5. Performance Risks

### RISK-PERF-01 — Registry Snapshot Causing Noticeable I/O Latency
**Rating:** Medium  
**Description:** Writing a large compressed registry snapshot during the installer's critical path may cause disk I/O contention.

**Impact:** Installation slower; installer I/O impacted; snapshot takes too long.

**Mitigation:**
1. Registry snapshots run on a dedicated background thread with `ThreadPriority.BelowNormal`.
2. Write compressed snapshot using streaming GZip to minimize peak I/O.
3. Pre-snapshot must complete before installer launches; post-snapshot runs after installer exits — no contention with installer I/O.

---

### RISK-PERF-02 — FileSystemWatcher Event Storm on Large Installations
**Rating:** High  
**Description:** Large installers (e.g., Visual Studio, Autodesk products) may create hundreds of thousands of files, saturating the FS event buffer and exceeding the 10,000 event cap quickly.

**Impact:** Cap hit early; many installation files not tracked; partial filesystem data.

**Mitigation:**
1. Apply early noise filters: ignore `*.tmp`, `~$*`, files in `%TEMP%` sub-paths.
2. Batch events with a 100ms coalescing window: multiple rapid events on the same path counted as one.
3. Prioritize events in `System32`, `Program Files`, `Run` keys directories over less critical paths.
4. Document cap and coalescing behavior in report metadata.
5. Cap is configurable per deployment; large-installer scenarios can increase cap in config.

---

### RISK-PERF-03 — WMI Process Event Subscription CPU Cost
**Rating:** Medium  
**Description:** `ManagementEventWatcher` with `Win32_ProcessStartTrace` can consume significant CPU on systems with high process creation rates (e.g., build systems, CI runners).

**Impact:** Agent exceeds 5% CPU target; impacts host performance.

**Mitigation:**
1. Apply WQL filter to subscription: only track processes where `ParentProcessID` is in the monitored PID set.
2. If CPU overhead exceeds threshold (monitored via self-sampling), automatically drop to polling mode and log the switch.
3. Polling mode interval: configurable, default 2 seconds.

---

### RISK-PERF-04 — Consolidated Report JSON Serialization OOM
**Rating:** Low  
**Description:** A very large session (many FS events, many event log entries, large MSI log) could produce a consolidated report that exceeds available memory during JSON serialization.

**Impact:** Report generation fails; OOM exception.

**Mitigation:**
1. Use streaming JSON serialization (`System.Text.Json` `Utf8JsonWriter`) rather than materializing the full object graph.
2. Apply per-collection caps (§2 Scalability Requirements) to bound maximum report size.
3. If report exceeds 50 MB, write arrays as separate referenced files and include paths in the report rather than inline embedding.
