# Folder Structure Specification
## SmartInstall AI — Full System (Phase 1 + Future Phases)
**Version:** 1.0  
**Date:** 2026-06-01  
**Status:** Draft  

---

## Design Principles

1. **Phase separation:** Phase 1 (agent + log collection) lives in `src/Agent`. Future phases (RAG, AI) add new top-level modules without touching Phase 1 code.
2. **Interface-first layout:** Interfaces and contracts in `Core`; implementations in named modules.
3. **Test proximity:** Tests live alongside source in a parallel `tests/` tree mirroring `src/`.
4. **Config separation:** All environment-specific configuration outside source tree.
5. **Schema versioning:** JSON schemas versioned and co-located with docs.

---

## Repository Root

```
smartinstaller_AI/
│
├── README.md
├── CLAUDE.md                          ← Architecture context for AI-assisted development
├── .gitignore
├── smartinstaller.sln                 ← Solution file
│
├── docs/                              ← All specification documents
│   ├── prd.md
│   ├── functional-spec.md
│   ├── non-functional-spec.md
│   ├── architecture.md
│   ├── data-model.md
│   ├── api-contracts.md
│   ├── folder-structure.md
│   ├── sequence-diagrams.md
│   ├── risk-analysis.md
│   ├── implementation-roadmap.md
│   └── schemas/
│       └── consolidated_report.v1.schema.json
│
├── config/
│   ├── smartinstall.config.json       ← Default agent configuration
│   └── smartinstall.config.schema.json ← Config JSON schema
│
├── src/
│   │
│   ├── Core/                          ← Shared contracts, models, interfaces (no implementation)
│   │   ├── SmartInstall.Core.csproj
│   │   ├── Interfaces/
│   │   │   ├── IInstallationAgent.cs
│   │   │   ├── ISessionManager.cs
│   │   │   ├── IInstallerRunner.cs
│   │   │   ├── ICollector.cs
│   │   │   ├── IEventCollector.cs
│   │   │   ├── IMSICollector.cs
│   │   │   ├── IWERCollector.cs
│   │   │   ├── IRegistryMonitor.cs
│   │   │   ├── IFilesystemMonitor.cs
│   │   │   ├── IProcessMonitor.cs
│   │   │   └── ILogCollector.cs
│   │   ├── Models/
│   │   │   ├── InstallationSession.cs
│   │   │   ├── InstallerResult.cs
│   │   │   ├── EventLogEntry.cs
│   │   │   ├── MSIError.cs
│   │   │   ├── MSIWarning.cs
│   │   │   ├── CrashReport.cs
│   │   │   ├── FileSystemEvent.cs
│   │   │   ├── RegistryChange.cs
│   │   │   ├── ProcessInfo.cs
│   │   │   ├── ResourceSample.cs
│   │   │   ├── CollectionError.cs
│   │   │   └── ConsolidatedInstallationReport.cs
│   │   ├── Enums/
│   │   │   ├── SessionStatus.cs
│   │   │   ├── InstallerType.cs
│   │   │   ├── InstallationOutcome.cs
│   │   │   ├── EventLevel.cs
│   │   │   ├── FSEventType.cs
│   │   │   └── RegistryChangeType.cs
│   │   └── Results/
│   │       ├── Result.cs              ← Result<T> monad
│   │       ├── CollectionResult.cs
│   │       └── ApiError.cs
│   │
│   ├── Agent/                         ← Phase 1: Installation Agent + Log Collection
│   │   ├── SmartInstall.Agent.csproj
│   │   ├── Program.cs                 ← CLI entry point
│   │   ├── ServiceRegistration.cs     ← DI container wiring
│   │   │
│   │   ├── Session/
│   │   │   ├── InstallationAgent.cs
│   │   │   ├── SessionManager.cs
│   │   │   └── SessionStateValidator.cs
│   │   │
│   │   ├── Runners/
│   │   │   ├── ExeInstallerRunner.cs
│   │   │   ├── MsiInstallerRunner.cs
│   │   │   └── InstallerRunnerFactory.cs
│   │   │
│   │   ├── Collectors/
│   │   │   ├── EventLogCollector.cs
│   │   │   ├── MsiCollector.cs
│   │   │   ├── WerCollector.cs
│   │   │   ├── RegistryMonitor.cs
│   │   │   ├── FilesystemMonitor.cs
│   │   │   └── ProcessMonitor.cs
│   │   │
│   │   ├── Aggregation/
│   │   │   ├── LogCollector.cs
│   │   │   ├── OutcomeCalculator.cs
│   │   │   ├── DiagnosticScoreCalculator.cs
│   │   │   └── ReportSerializer.cs
│   │   │
│   │   ├── Infrastructure/
│   │   │   ├── EventBus.cs
│   │   │   ├── ConfigProvider.cs
│   │   │   ├── PrivilegeChecker.cs
│   │   │   ├── CredentialRedactor.cs
│   │   │   ├── SessionsIndexWriter.cs
│   │   │   └── CollectorTimeoutWrapper.cs
│   │   │
│   │   └── Parsing/
│   │       ├── MsiLogParser.cs
│   │       └── WerReportParser.cs
│   │
│   ├── Ingestion/                     ← Phase 2: ChromaDB / Vector Store ingestion (FUTURE)
│   │   └── .gitkeep
│   │
│   ├── AI/                            ← Phase 3: Ollama / SLM / RAG pipeline (FUTURE)
│   │   └── .gitkeep
│   │
│   └── Dashboard/                     ← Phase 4: Web dashboard / API (FUTURE)
│       └── .gitkeep
│
├── tests/
│   │
│   ├── SmartInstall.Core.Tests/
│   │   ├── SmartInstall.Core.Tests.csproj
│   │   └── Models/
│   │       └── ConsolidatedReportTests.cs
│   │
│   ├── SmartInstall.Agent.Tests/
│   │   ├── SmartInstall.Agent.Tests.csproj
│   │   ├── Session/
│   │   │   ├── SessionManagerTests.cs
│   │   │   └── SessionStateValidatorTests.cs
│   │   ├── Runners/
│   │   │   ├── ExeInstallerRunnerTests.cs
│   │   │   └── MsiInstallerRunnerTests.cs
│   │   ├── Collectors/
│   │   │   ├── EventLogCollectorTests.cs
│   │   │   ├── MsiCollectorTests.cs
│   │   │   ├── WerCollectorTests.cs
│   │   │   ├── RegistryMonitorTests.cs
│   │   │   ├── FilesystemMonitorTests.cs
│   │   │   └── ProcessMonitorTests.cs
│   │   ├── Aggregation/
│   │   │   ├── LogCollectorTests.cs
│   │   │   ├── OutcomeCalculatorTests.cs
│   │   │   └── DiagnosticScoreCalculatorTests.cs
│   │   ├── Infrastructure/
│   │   │   ├── CredentialRedactorTests.cs
│   │   │   └── ConfigProviderTests.cs
│   │   └── Parsing/
│   │       ├── MsiLogParserTests.cs
│   │       └── WerReportParserTests.cs
│   │
│   └── SmartInstall.IntegrationTests/
│       ├── SmartInstall.IntegrationTests.csproj
│       ├── Fixtures/
│       │   ├── SucceedInstaller/       ← Test MSI that installs successfully
│       │   ├── FailInstaller/          ← Test MSI that returns 1603
│       │   └── CrashInstaller/        ← Test EXE that triggers access violation
│       └── Scenarios/
│           ├── SuccessfulInstallTests.cs
│           ├── FailedInstallTests.cs
│           ├── MsiFailureTests.cs
│           ├── CrashTests.cs
│           └── PartialCollectorFailureTests.cs
│
├── scripts/
│   ├── Install-Agent.ps1              ← Deployment PowerShell script
│   ├── Build-Release.ps1              ← Self-contained publish script
│   └── Run-Tests.ps1                  ← Test execution script
│
└── artifacts/                         ← Build output (gitignored)
    └── .gitkeep
```

---

## Runtime Output Structure

The agent writes all session data to a configurable output root. Default: `C:\ProgramData\SmartInstallAI\`.

```
C:\ProgramData\SmartInstallAI\
│
├── smartinstall.config.json           ← Active configuration (copied from config/ on install)
├── agent.log                          ← Structured agent internal log (Serilog JSON sink)
├── sessions_index.json                ← Global index of all sessions
│
└── sessions\
    └── <SessionId>\                   ← e.g., 3f7a1d2c-8e4b-4f9a-b2c1-9d0e5f3a7b8c\
        ├── session.json               ← Session metadata + state
        ├── stdout.log                 ← Installer STDOUT (timestamped lines)
        ├── stderr.log                 ← Installer STDERR (timestamped lines)
        ├── msi_verbose.log            ← MSI verbose log (raw, written by msiexec)
        ├── msi_errors.json            ← Parsed MSI errors and warnings
        ├── event_log_delta.json       ← Windows Event Log delta
        ├── registry_pre.json.gz       ← Pre-installation registry snapshot (compressed)
        ├── registry_delta.json        ← Registry changes (added/modified/deleted)
        ├── filesystem_events.json     ← Filesystem change events
        ├── crash_reports.json         ← WER crash report data
        ├── process_tree.json          ← Installer process tree
        ├── process_resource.json      ← CPU/memory samples
        └── consolidated_report.json   ← Final aggregated report
```

---

## Project References

```
SmartInstall.Agent → SmartInstall.Core
SmartInstall.Agent.Tests → SmartInstall.Agent, SmartInstall.Core
SmartInstall.Core.Tests → SmartInstall.Core
SmartInstall.IntegrationTests → SmartInstall.Agent, SmartInstall.Core

(Future)
SmartInstall.Ingestion → SmartInstall.Core
SmartInstall.AI → SmartInstall.Core, SmartInstall.Ingestion
SmartInstall.Dashboard → SmartInstall.Core, SmartInstall.Agent (API)
```

---

## NuGet Dependencies (Phase 1)

| Package | Version | Purpose |
|---------|---------|---------|
| `Microsoft.Extensions.DependencyInjection` | 8.x | DI container |
| `Microsoft.Extensions.Hosting` | 8.x | Hosted service lifecycle |
| `Serilog` | 4.x | Structured logging |
| `Serilog.Sinks.File` | 5.x | File log sink |
| `Serilog.Sinks.Console` | 5.x | Console log sink |
| `System.CommandLine` | 2.x | CLI argument parsing |
| `System.Management` | 8.x | WMI access |
| `JsonSchema.Net` | 7.x | JSON schema validation |

**Intentionally excluded from Phase 1:**
- No ChromaDB client
- No Ollama client
- No ML.NET
- No vector embedding libraries
- No HTTP client libraries (no network calls)
