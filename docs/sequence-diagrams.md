# Sequence Diagrams
## SmartInstall AI — Installation Agent & Log Collection Layer
**Version:** 1.0  
**Date:** 2026-06-01  
**Status:** Draft  

---

## 1. Successful Installation Flow

```mermaid
sequenceDiagram
    autonumber
    actor Caller as Caller (CLI / Script)
    participant Agent as InstallationAgent
    participant SM as SessionManager
    participant PC as PrivilegeChecker
    participant CFG as ConfigProvider
    participant IR as InstallerRunner
    participant EC as EventCollector
    participant RM as RegistryMonitor
    participant FSM as FilesystemMonitor
    participant PM as ProcessMonitor
    participant WER as WERCollector
    participant MSI as MSICollector
    participant LC as LogCollector
    participant FS as FileSystem (Output)

    Caller->>Agent: StartSession(installerPath, options)
    Agent->>PC: ValidatePrivileges()
    PC-->>Agent: OK

    Agent->>CFG: LoadConfig()
    CFG-->>Agent: Config

    Agent->>SM: CreateSession(request)
    SM->>FS: Write session.json (Initializing)
    SM-->>Agent: InstallationSession{SessionId}

    Note over Agent: State → PreSnapshotting

    par Pre-installation Snapshots (parallel)
        Agent->>EC: TakePreSnapshot(sessionId)
        EC-->>Agent: OK (watermarks recorded)
    and
        Agent->>RM: TakePreSnapshot(sessionId)
        RM->>FS: Write registry_pre.json.gz
        RM-->>Agent: OK
    and
        Agent->>WER: TakePreSnapshot(sessionId)
        WER-->>Agent: OK (WER dir snapshot)
    end

    Agent->>FSM: StartWatching(sessionId)
    FSM-->>Agent: OK (watchers active)

    Note over Agent: State → Installing

    Agent->>IR: Launch(installerPath, sessionDir)
    IR->>FS: Create stdout.log, stderr.log
    IR-->>Agent: InstallerRunResult{pid, startTimestamp}

    Agent->>PM: StartTracking(sessionId, pid)
    PM-->>Agent: OK (WMI subscriptions active)

    Note over IR,PM: Installer runs...
    loop During Installation
        IR->>FS: Append STDOUT/STDERR lines
        FSM->>FS: Buffer FS events (created/modified/deleted)
        PM->>PM: Sample CPU/Memory every 5s
    end

    IR->>Agent: Process Exited (exitCode=0)

    Note over Agent: State → PostSnapshotting

    Agent->>PM: StopTracking(sessionId)
    PM->>FS: Write process_tree.json, process_resource.json
    PM-->>Agent: ProcessMonitorResult

    Agent->>FSM: StopWatching(sessionId)
    FSM->>FS: Write filesystem_events.json
    FSM-->>Agent: FilesystemEventResult

    par Post-installation Snapshots (parallel)
        Agent->>EC: TakePostSnapshot(sessionId)
        EC->>FS: Write event_log_delta.json
        EC-->>Agent: EventLogDeltaResult
    and
        Agent->>RM: TakePostSnapshot(sessionId)
        RM->>FS: Write registry_delta.json
        RM-->>Agent: RegistryDeltaResult
    and
        Agent->>WER: TakePostSnapshot(sessionId)
        WER-->>Agent: WERCollectionResult{crashDetected=false}
    and
        Agent->>MSI: TakePostSnapshot(sessionId)
        MSI->>FS: Parse msi_verbose.log
        MSI-->>Agent: MSICollectionResult{errors=[], warnings=[]}
    end

    Note over Agent: State → Aggregating

    Agent->>LC: Aggregate(allResults)
    LC->>FS: Write consolidated_report.json
    LC->>FS: Append to sessions_index.json
    LC-->>Agent: AggregationResponse{outcome=Success, score=5}

    Agent->>SM: FinalizeSession(exitCode=0, outcome=Success)
    SM->>FS: Update session.json (Completed)

    Agent-->>Caller: WaitResponse{outcome=Success, exitCode=0, reportPath=...}
```

---

## 2. Failed Installation Flow

```mermaid
sequenceDiagram
    autonumber
    actor Caller as Caller (CLI / Script)
    participant Agent as InstallationAgent
    participant SM as SessionManager
    participant IR as InstallerRunner
    participant EC as EventCollector
    participant RM as RegistryMonitor
    participant FSM as FilesystemMonitor
    participant PM as ProcessMonitor
    participant MSI as MSICollector
    participant WER as WERCollector
    participant LC as LogCollector
    participant FS as FileSystem (Output)

    Caller->>Agent: StartSession(installerPath, options)
    Note over Agent: [Startup, pre-snapshots, watchers same as Successful flow — steps 1–14 abbreviated]
    Agent->>IR: Launch(installerPath, sessionDir)
    IR-->>Agent: InstallerRunResult{pid}
    Agent->>PM: StartTracking(sessionId, pid)

    Note over IR: Installer encounters fatal error...

    IR->>FS: Append error lines to stderr.log
    IR->>Agent: Process Exited (exitCode=1603)

    Agent->>PM: StopTracking(sessionId)
    PM-->>Agent: ProcessMonitorResult{peakCpu=78%, peakMem=512MB}

    Agent->>FSM: StopWatching(sessionId)
    FSM-->>Agent: FilesystemEventResult{eventCount=342}

    par Post-snapshots
        Agent->>EC: TakePostSnapshot(sessionId)
        EC->>FS: Write event_log_delta.json
        Note over EC: Finds 4 Error-level entries in Application log
        EC-->>Agent: EventLogDeltaResult{highSeverityCount=4}
    and
        Agent->>RM: TakePostSnapshot(sessionId)
        RM-->>Agent: RegistryDeltaResult{changeCount=12}
    and
        Agent->>WER: TakePostSnapshot(sessionId)
        WER-->>Agent: WERCollectionResult{crashDetected=false}
    and
        Agent->>MSI: TakePostSnapshot(sessionId)
        Note over MSI: Parses verbose log — finds "Return value 3"
        MSI-->>Agent: MSICollectionResult{errors=[{isFatal=true,...}], errorCount=3}
    end

    Agent->>LC: Aggregate(allResults)
    Note over LC: outcome=Failure, diagnosticScore=72 (high: fatal MSI error + 4 event log errors)
    LC->>FS: Write consolidated_report.json
    LC-->>Agent: AggregationResponse{outcome=Failure, score=72}

    Agent->>SM: FinalizeSession(exitCode=1603, outcome=Failure)
    SM->>FS: Update session.json (Completed, Failure)

    Agent-->>Caller: WaitResponse{outcome=Failure, exitCode=1603, reportPath=...}
    Note over Caller: Agent process exits with code 1
```

---

## 3. MSI-Specific Failure Flow

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant Agent as InstallationAgent
    participant IR as InstallerRunner
    participant MSI as MSICollector
    participant EC as EventCollector
    participant WER as WERCollector
    participant LC as LogCollector
    participant FS as FileSystem (Output)

    Caller->>Agent: StartSession(installerPath="setup.msi", type=MSI)

    Note over Agent: Pre-snapshots taken (abbreviated)

    Agent->>MSI: GetMsiLogPath(sessionId)
    MSI-->>Agent: "<sessionDir>\msi_verbose.log"

    Agent->>IR: Launch("msiexec.exe /i setup.msi /l*v <logPath> /qn /norestart")
    IR-->>Agent: InstallerRunResult{pid=4832}

    Note over IR: msiexec begins installation actions...

    IR->>FS: msi_verbose.log grows line by line
    IR->>FS: STDOUT captures msiexec progress

    Note over IR: Action "InstallFiles" fails — returns value 3

    IR->>Agent: Process Exited (exitCode=1603)

    Agent->>MSI: TakePostSnapshot(sessionId)
    MSI->>FS: Read msi_verbose.log (full parse)

    Note over MSI: Regex scan finds:<br/>- "Return value 3" at line 2847<br/>- 2 ERROR lines preceding it<br/>- 1 WARNING line

    MSI-->>Agent: MSICollectionResult {
        errors: [
          {lineNumber:2843, actionName:"InstallFiles", isFatal:false},
          {lineNumber:2847, actionName:"InstallFinalize", isFatal:true}
        ],
        warnings: [{lineNumber:1203, isCancelled:false}],
        fatalErrorDetected: true
    }

    Agent->>EC: TakePostSnapshot(sessionId)
    Note over EC: Finds EventID 11708 (product installation failed) in Application log
    EC-->>Agent: EventLogDeltaResult{entries=[{eventId:11708, level:Error}]}

    Agent->>WER: TakePostSnapshot(sessionId)
    WER-->>Agent: WERCollectionResult{crashDetected=false}

    Agent->>LC: Aggregate(allResults)
    Note over LC: Computes:<br/>outcome = Failure<br/>score = 85 (fatal MSI + event log error + failed action)
    LC->>FS: Write consolidated_report.json
    LC-->>Agent: AggregationResponse{outcome=Failure, score=85}

    Agent-->>Caller: WaitResponse{outcome=Failure, exitCode=1603}
    Note over Caller: Agent exits with code 1
```

---

## 4. Installer Crash Flow

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant Agent as InstallationAgent
    participant IR as InstallerRunner
    participant PM as ProcessMonitor
    participant WER as WERCollector
    participant EC as EventCollector
    participant MSI as MSICollector
    participant LC as LogCollector
    participant FS as FileSystem (Output)

    Caller->>Agent: StartSession(installerPath="setup.exe")

    Note over Agent: Pre-snapshots taken (abbreviated)

    Agent->>IR: Launch("setup.exe")
    IR-->>Agent: InstallerRunResult{pid=7720}
    Agent->>PM: StartTracking(sessionId, pid=7720)

    Note over IR: Installer process crashes (access violation)...

    IR->>FS: Append crash-related output to stderr.log
    IR->>Agent: Process Exited (exitCode=-1073741819 = 0xC0000005)

    Note over WER: OS writes WER report to ReportQueue asynchronously

    Agent->>PM: StopTracking(sessionId)
    PM-->>Agent: ProcessMonitorResult

    Note over Agent: Wait 5 seconds for async WER report write

    Agent->>WER: TakePostSnapshot(sessionId)
    WER->>FS: Scan WER ReportQueue for new directories

    Note over WER: Finds new report dir "AppCrash_setup.exe_..."<br/>Parses Report.wer

    WER-->>Agent: WERCollectionResult {
        crashDetected: true,
        crashReports: [{
          appName: "setup.exe",
          exceptionCode: "0xC0000005",
          moduleName: "setup.exe",
          offset: "0x00012abc",
          eventTime: "2026-06-01T10:32:14Z",
          dumpFilePath: "C:\...\WER\...\AppCrash.dmp",
          isInInstallerTree: true
        }]
    }

    Agent->>EC: TakePostSnapshot(sessionId)
    Note over EC: Finds EventID 1000 (AppCrash) in Application log
    EC-->>Agent: EventLogDeltaResult{entries=[{eventId:1000, level:Error, source:"Application Error"}]}

    Agent->>MSI: TakePostSnapshot(sessionId)
    Note over MSI: No msi_verbose.log exists (EXE crashed before invoking msiexec)
    MSI-->>Agent: MSICollectionResult{verboseLogPath=null, errors=[], warnings=[]}

    Agent->>LC: Aggregate(allResults)
    Note over LC: Computes:<br/>outcome = Crashed<br/>score = 95 (crash + exception code + event log error)
    LC->>FS: Write consolidated_report.json
    LC-->>Agent: AggregationResponse{outcome=Crashed, score=95}

    Agent->>Agent: FinalizeSession(exitCode=0xC0000005, outcome=Crashed)
    Agent-->>Caller: WaitResponse{outcome=Crashed, exitCode=-1073741819}
    Note over Caller: Agent exits with code 2
```

---

## 5. Collector Partial Failure Flow

Illustrates graceful degradation when one collector fails but the session continues.

```mermaid
sequenceDiagram
    autonumber
    participant Agent as InstallationAgent
    participant RM as RegistryMonitor
    participant EC as EventCollector
    participant FSM as FilesystemMonitor
    participant LC as LogCollector
    participant FS as FileSystem (Output)

    Note over Agent: Session in progress — post-install phase

    par Post-snapshots (parallel)
        Agent->>RM: TakePostSnapshot(sessionId)
        Note over RM: Registry snapshot fails — key ACL denies access
        RM-->>Agent: Result.Failure{code="REGISTRY_KEY_ACCESS_DENIED"}
    and
        Agent->>EC: TakePostSnapshot(sessionId)
        EC-->>Agent: Result.Success{EventLogDeltaResult}
    and
        Agent->>FSM: StopWatching(sessionId)
        FSM-->>Agent: Result.Success{FilesystemEventResult}
    end

    Agent->>Agent: RecordCollectionError("RegistryMonitor", "REGISTRY_KEY_ACCESS_DENIED")
    Note over Agent: Session continues — partial data used

    Agent->>LC: Aggregate(results, collectionErrors=[{collector:"RegistryMonitor",...}])

    Note over LC: Report generated with:<br/>registryChanges = []<br/>collectionErrors = [{collector: "RegistryMonitor", ...}]<br/>outcome = Failure (due to installer exit code)<br/>score = 45 (reduced confidence — partial data)

    LC->>FS: Write consolidated_report.json (with collectionErrors array populated)
    LC-->>Agent: AggregationResponse{outcome=Failure, score=45}

    Note over Agent: Session completes normally<br/>Consumer sees collectionErrors and knows registry data is missing
```
