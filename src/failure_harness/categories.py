"""Failure category definitions and simulated error payloads."""

from __future__ import annotations

from dataclasses import dataclass

from failure_harness.models import FailureCategory, FailureSeverity


@dataclass(frozen=True, slots=True)
class FailureTemplate:
    """Template for generating installer-visible failure symptoms."""

    category: FailureCategory
    sub_type: str
    exit_code: int
    stderr_message: str
    stdout_message: str
    log_lines: tuple[str, ...]
    default_keywords: tuple[str, ...]


_FAILURE_TEMPLATES: dict[tuple[FailureCategory, str], FailureTemplate] = {}


def _register(template: FailureTemplate) -> None:
    _FAILURE_TEMPLATES[(template.category, template.sub_type)] = template


def get_failure_template(category: FailureCategory, sub_type: str) -> FailureTemplate:
    key = (category, sub_type)
    if key not in _FAILURE_TEMPLATES:
        available = [f"{c.value}/{s}" for c, s in _FAILURE_TEMPLATES]
        raise KeyError(
            f"Unknown failure sub_type '{sub_type}' for category '{category.value}'. "
            f"Available: {', '.join(sorted(available)[:20])}..."
        )
    return _FAILURE_TEMPLATES[key]


def list_sub_types(category: FailureCategory) -> list[str]:
    return sorted(sub for cat, sub in _FAILURE_TEMPLATES if cat == category)


# --- Category 1: Download & Acquisition ---
_register(
    FailureTemplate(
        FailureCategory.DOWNLOAD_ACQUISITION,
        "corrupt_download",
        1619,
        "ERROR: Downloaded package failed integrity verification (corrupt archive).",
        "Downloading setup payload from CDN...",
        ("Checksum mismatch: expected SHA256 abc123, got def456", "Package verification failed"),
        ("corrupt", "checksum", "download", "integrity"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DOWNLOAD_ACQUISITION,
        "partial_download",
        1619,
        "ERROR: Incomplete download — connection reset before transfer completed.",
        "Download progress: 67%",
        ("Partial download detected", "Expected 450MB, received 301MB"),
        ("partial", "download", "incomplete", "network"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DOWNLOAD_ACQUISITION,
        "invalid_checksum",
        1619,
        "ERROR: Package checksum validation failed.",
        "Verifying package signature...",
        ("Invalid checksum for setup.msi",),
        ("checksum", "verification", "package"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DOWNLOAD_ACQUISITION,
        "cdn_unavailable",
        1601,
        "ERROR: CDN endpoint unreachable (HTTP 503 Service Unavailable).",
        "Connecting to download.akamai.example.com...",
        ("CDN unavailable", "HTTP 503"),
        ("cdn", "unavailable", "503", "network"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DOWNLOAD_ACQUISITION,
        "auth_token_failure",
        1603,
        "ERROR: Authentication token rejected (401 Unauthorized).",
        "Requesting download authorization...",
        ("Token validation failed", "401 Unauthorized"),
        ("authentication", "token", "401"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DOWNLOAD_ACQUISITION,
        "proxy_issue",
        1603,
        "ERROR: Proxy connection failed — unable to reach download server.",
        "Using system proxy settings...",
        ("Proxy authentication required", "Connection refused via proxy"),
        ("proxy", "connection", "network"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DOWNLOAD_ACQUISITION,
        "vpn_restriction",
        1603,
        "ERROR: VPN policy blocks download endpoint.",
        "Checking network policy...",
        ("VPN restriction active", "Download blocked by corporate policy"),
        ("vpn", "network", "policy", "blocked"),
    )
)

# --- Category 2: Disk & Storage ---
_register(
    FailureTemplate(
        FailureCategory.DISK_STORAGE,
        "insufficient_disk_space",
        112,
        "ERROR: Not enough disk space. Required: 2048 MB, Available: 128 MB.",
        "Checking disk space on target drive...",
        ("Insufficient disk space", "No space left on device"),
        ("disk", "space", "storage", "full"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DISK_STORAGE,
        "invalid_install_path",
        1603,
        "ERROR: Installation path is invalid or inaccessible.",
        "Validating installation directory...",
        ("Invalid installation path", "Path contains illegal characters"),
        ("path", "invalid", "directory"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DISK_STORAGE,
        "temp_corruption",
        1603,
        "ERROR: Temporary directory is corrupted or unreadable.",
        "Writing to %TEMP%\\TestAppSetup...",
        ("Temp directory corruption detected", "Write failed: data error"),
        ("temp", "corruption", "directory"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DISK_STORAGE,
        "read_only_destination",
        5,
        "ERROR: Destination folder is read-only.",
        "Creating installation directory...",
        ("Access denied: read-only destination",),
        ("read-only", "access", "denied", "permission"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DISK_STORAGE,
        "filesystem_access_failure",
        1603,
        "ERROR: Filesystem access failure (I/O error 0x80070020).",
        "Copying files to Program Files...",
        ("Filesystem I/O error", "Sharing violation"),
        ("filesystem", "access", "io error"),
    )
)

# --- Category 3: Permissions & Security ---
_register(
    FailureTemplate(
        FailureCategory.PERMISSIONS_SECURITY,
        "missing_admin",
        1603,
        "ERROR: Administrator privileges required but not granted.",
        "Checking elevation status...",
        ("Administrator privileges required", "Access is denied"),
        ("administrator", "elevation", "privileges", "UAC"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.PERMISSIONS_SECURITY,
        "uac_denial",
        1223,
        "ERROR: User cancelled UAC elevation request.",
        "Requesting elevation via UAC...",
        ("UAC denied by user", "Operation cancelled by user"),
        ("UAC", "cancelled", "elevation"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.PERMISSIONS_SECURITY,
        "enterprise_policy",
        1625,
        "ERROR: Installation blocked by enterprise Group Policy.",
        "Checking AppLocker / Software Restriction Policy...",
        ("Blocked by Group Policy", "Enterprise policy restriction"),
        ("policy", "group policy", "enterprise", "blocked"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.PERMISSIONS_SECURITY,
        "antivirus_interference",
        1603,
        "ERROR: Antivirus quarantined installer component.",
        "Extracting setup files...",
        ("Threat detected and quarantined", "Real-time protection blocked file"),
        ("antivirus", "quarantine", "blocked", "security"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.PERMISSIONS_SECURITY,
        "edr_blocking",
        1603,
        "ERROR: EDR agent blocked installation process.",
        "Launching setup engine...",
        ("EDR blocked process execution", "Behavioral threat detected"),
        ("EDR", "blocked", "security"),
    )
)

# --- Category 4: Dependency ---
_register(
    FailureTemplate(
        FailureCategory.DEPENDENCY,
        "missing_vc_runtime",
        1603,
        "ERROR: Microsoft Visual C++ 2015-2022 Redistributable (x64) not found.",
        "Checking prerequisites...",
        ("Missing VC++ Runtime", "vcruntime140.dll not found"),
        ("vc++", "runtime", "redistributable", "prerequisite"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DEPENDENCY,
        "missing_dotnet",
        1603,
        "ERROR: .NET Runtime 8.0 or later is required.",
        "Checking .NET installation...",
        ("Missing .NET Runtime", ".NET Framework not installed"),
        ("dotnet", ".net", "runtime", "prerequisite"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DEPENDENCY,
        "missing_prerequisite",
        1603,
        "ERROR: Required prerequisite installer failed.",
        "Running prerequisite: DirectX End-User Runtime...",
        ("Prerequisite installation failed",),
        ("prerequisite", "dependency", "failed"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.DEPENDENCY,
        "licensing_service_unavailable",
        1603,
        "ERROR: Licensing prerequisite service is unavailable.",
        "Connecting to licensing service...",
        ("Licensing service unavailable",),
        ("licensing", "service", "unavailable"),
    )
)

# --- Category 5: Version Compatibility ---
_register(
    FailureTemplate(
        FailureCategory.VERSION_COMPATIBILITY,
        "unsupported_os",
        1603,
        "ERROR: Operating system version not supported (requires Windows 10 22H2+).",
        "Checking OS compatibility...",
        ("Unsupported OS version", "Windows 7 detected"),
        ("unsupported", "operating system", "version"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.VERSION_COMPATIBILITY,
        "architecture_mismatch",
        1603,
        "ERROR: 64-bit installer cannot run on 32-bit OS.",
        "Checking CPU architecture...",
        ("Architecture mismatch", "x64 required"),
        ("architecture", "x64", "x86", "mismatch"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.VERSION_COMPATIBILITY,
        "plugin_incompatibility",
        1603,
        "ERROR: Installed plugin version incompatible with this release.",
        "Validating plugin compatibility...",
        ("Plugin incompatibility", "API version mismatch"),
        ("plugin", "incompatible", "version"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.VERSION_COMPATIBILITY,
        "side_by_side_conflict",
        1638,
        "ERROR: Another version of this product is already installed.",
        "Checking for existing installation...",
        ("Side-by-side conflict", "Another version already installed"),
        ("side-by-side", "conflict", "version", "installed"),
    )
)

# --- Category 6: Registry ---
_register(
    FailureTemplate(
        FailureCategory.REGISTRY,
        "registry_corruption",
        1603,
        "ERROR: Registry corruption detected during key write.",
        "Writing registry keys...",
        ("Registry corruption", "Cannot open registry key"),
        ("registry", "corruption", "key"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.REGISTRY,
        "missing_registry_key",
        1603,
        "ERROR: Required registry key not found.",
        "Reading HKLM\\SOFTWARE\\TestApp...",
        ("Missing registry key",),
        ("registry", "missing", "key"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.REGISTRY,
        "registry_permission",
        5,
        "ERROR: Access denied writing to registry hive.",
        "Creating uninstall registry entry...",
        ("Registry permission denied",),
        ("registry", "permission", "access denied"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.REGISTRY,
        "com_registration_failure",
        1603,
        "ERROR: COM component registration failed (regsvr32 exit 0x80004005).",
        "Registering COM components...",
        ("COM registration failed", "regsvr32 failed"),
        ("COM", "registration", "regsvr32"),
    )
)

# --- Category 7: Service ---
_register(
    FailureTemplate(
        FailureCategory.SERVICE,
        "licensing_daemon_unavailable",
        1603,
        "ERROR: Licensing daemon service is not running.",
        "Starting FlexNet Licensing Service...",
        ("Licensing daemon unavailable", "Service not started"),
        ("licensing", "daemon", "service"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.SERVICE,
        "service_startup_failure",
        1603,
        "ERROR: TestAppService failed to start (Error 1053).",
        "Starting Windows service...",
        ("Service startup failure", "Error 1053"),
        ("service", "startup", "1053"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.SERVICE,
        "service_dependency_failure",
        1603,
        "ERROR: Dependent service RpcSs is not running.",
        "Checking service dependencies...",
        ("Service dependency failure",),
        ("service", "dependency", "failed"),
    )
)

# --- Category 8: Installer Engine ---
_register(
    FailureTemplate(
        FailureCategory.INSTALLER_ENGINE,
        "msi_rollback",
        1603,
        "ERROR: Installation failed — MSI rollback initiated.",
        "Installing MSI package...",
        ("MSI rollback", "Installation failed, rolling back changes"),
        ("MSI", "rollback", "1603"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.INSTALLER_ENGINE,
        "bootstrapper_failure",
        1603,
        "ERROR: Bootstrapper failed to launch main installer.",
        "Bootstrapper: extracting embedded MSI...",
        ("Bootstrapper failure",),
        ("bootstrapper", "failed"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.INSTALLER_ENGINE,
        "transaction_corruption",
        1603,
        "ERROR: Windows Installer transaction corrupted.",
        "Committing installation transaction...",
        ("Transaction corruption",),
        ("transaction", "corruption", "MSI"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.INSTALLER_ENGINE,
        "package_verification_failure",
        1620,
        "ERROR: Package verification failed — invalid or tampered MSI.",
        "Verifying MSI package...",
        ("Package verification failed", "Invalid package"),
        ("package", "verification", "MSI", "invalid"),
    )
)

# --- Category 9: File & Process Locking ---
_register(
    FailureTemplate(
        FailureCategory.FILE_PROCESS_LOCKING,
        "locked_dll",
        1603,
        "ERROR: Cannot overwrite locked DLL (testapp_core.dll in use).",
        "Updating application binaries...",
        ("Locked DLL", "File in use by another process"),
        ("locked", "DLL", "in use"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.FILE_PROCESS_LOCKING,
        "locked_file",
        1603,
        "ERROR: Target file is locked by another process.",
        "Copying testapp.exe...",
        ("File locked", "Sharing violation"),
        ("locked", "file", "sharing violation"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.FILE_PROCESS_LOCKING,
        "concurrent_installer",
        1618,
        "ERROR: Another installation is already in progress.",
        "Checking for concurrent installations...",
        ("Another installation in progress", "1618"),
        ("concurrent", "installation", "1618"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.FILE_PROCESS_LOCKING,
        "pending_reboot",
        3010,
        "ERROR: Pending reboot required before installation can continue.",
        "Checking pending file operations...",
        ("Pending reboot", "Restart required"),
        ("reboot", "pending", "restart"),
    )
)

# --- Category 10: OS-Level ---
_register(
    FailureTemplate(
        FailureCategory.OS_LEVEL,
        "wmi_corruption",
        1603,
        "ERROR: WMI repository corruption detected.",
        "Querying WMI for system info...",
        ("WMI corruption", "Invalid class"),
        ("WMI", "corruption"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.OS_LEVEL,
        "missing_system_component",
        1603,
        "ERROR: Required Windows component (Media Feature Pack) missing.",
        "Checking optional Windows features...",
        ("Missing system component",),
        ("component", "missing", "windows"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.OS_LEVEL,
        "windows_update_issue",
        1603,
        "ERROR: Pending Windows Update blocks installation.",
        "Checking Windows Update status...",
        ("Windows Update issue", "Updates pending"),
        ("windows update", "pending"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.OS_LEVEL,
        "environment_corruption",
        1603,
        "ERROR: System environment variables corrupted.",
        "Reading PATH environment...",
        ("Environment corruption",),
        ("environment", "PATH", "corruption"),
    )
)

# --- Category 11: GPU & Driver ---
_register(
    FailureTemplate(
        FailureCategory.GPU_DRIVER,
        "unsupported_gpu",
        1603,
        "ERROR: GPU not supported (minimum: DirectX 12 compatible).",
        "Detecting graphics hardware...",
        ("Unsupported GPU",),
        ("GPU", "unsupported", "graphics"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.GPU_DRIVER,
        "missing_opengl",
        1603,
        "ERROR: OpenGL 4.5 support not detected.",
        "Checking OpenGL version...",
        ("Missing OpenGL", "OpenGL not supported"),
        ("OpenGL", "graphics"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.GPU_DRIVER,
        "missing_directx",
        1603,
        "ERROR: DirectX 12 runtime not found.",
        "Checking DirectX...",
        ("Missing DirectX", "DirectX 12 required"),
        ("DirectX", "runtime"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.GPU_DRIVER,
        "outdated_driver",
        1603,
        "ERROR: Graphics driver outdated (minimum version 531.18).",
        "Checking driver version...",
        ("Outdated driver", "Update graphics driver"),
        ("driver", "outdated", "graphics"),
    )
)

# --- Category 12: Licensing ---
_register(
    FailureTemplate(
        FailureCategory.LICENSING,
        "token_validation_failure",
        1603,
        "ERROR: License token validation failed.",
        "Validating license token...",
        ("Token validation failed",),
        ("license", "token", "validation"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.LICENSING,
        "flexnet_failure",
        1603,
        "ERROR: FlexNet Licensing error -15,570 (License server unreachable).",
        "Connecting to license server...",
        ("FlexNet failure", "-15570"),
        ("FlexNet", "license", "server"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.LICENSING,
        "expired_license",
        1603,
        "ERROR: License expired on 2025-12-31.",
        "Checking license expiry...",
        ("Expired license",),
        ("license", "expired"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.LICENSING,
        "clock_skew",
        1603,
        "ERROR: System clock skew detected — license validation failed.",
        "Synchronizing license timestamp...",
        ("Clock skew", "Time synchronization"),
        ("clock", "skew", "license"),
    )
)

# --- Category 13: Cloud/API ---
_register(
    FailureTemplate(
        FailureCategory.CLOUD_API,
        "oauth_failure",
        1603,
        "ERROR: OAuth authentication failed (invalid_grant).",
        "Authenticating with cloud API...",
        ("OAuth failure", "invalid_grant"),
        ("OAuth", "authentication", "cloud"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.CLOUD_API,
        "api_timeout",
        1603,
        "ERROR: Cloud API request timed out after 30 seconds.",
        "Calling activation API...",
        ("API timeout", "Request timed out"),
        ("API", "timeout", "cloud"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.CLOUD_API,
        "telemetry_outage",
        0,
        "WARNING: Telemetry endpoint unreachable — continuing install.",
        "Sending telemetry heartbeat...",
        ("Telemetry outage",),
        ("telemetry", "outage"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.CLOUD_API,
        "cloud_licensing_failure",
        1603,
        "ERROR: Cloud licensing service returned HTTP 500.",
        "Activating cloud license...",
        ("Cloud licensing failure",),
        ("cloud", "licensing", "500"),
    )
)

# --- Category 14: Enterprise Deployment ---
_register(
    FailureTemplate(
        FailureCategory.ENTERPRISE_DEPLOYMENT,
        "sccm_conflict",
        1603,
        "ERROR: SCCM deployment conflict — package already assigned.",
        "Checking SCCM client status...",
        ("SCCM conflict",),
        ("SCCM", "deployment", "conflict"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.ENTERPRISE_DEPLOYMENT,
        "intune_sequencing",
        1603,
        "ERROR: Intune app sequencing dependency not satisfied.",
        "Checking Intune dependency chain...",
        ("Intune sequencing",),
        ("Intune", "sequencing"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.ENTERPRISE_DEPLOYMENT,
        "vdi_conflict",
        1603,
        "ERROR: VDI golden image conflict — read-only profile.",
        "Checking VDI environment...",
        ("VDI conflict",),
        ("VDI", "conflict"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.ENTERPRISE_DEPLOYMENT,
        "group_policy_restriction",
        1625,
        "ERROR: Group Policy restricts software installation.",
        "Checking GPO software restriction...",
        ("Group Policy restriction",),
        ("group policy", "restriction"),
    )
)

# --- Category 15: Update ---
_register(
    FailureTemplate(
        FailureCategory.UPDATE,
        "delta_patch_corruption",
        1603,
        "ERROR: Delta patch corrupted — full reinstall required.",
        "Applying delta update...",
        ("Delta patch corruption",),
        ("delta", "patch", "corruption"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.UPDATE,
        "baseline_mismatch",
        1603,
        "ERROR: Installed baseline version mismatch for patch.",
        "Verifying patch baseline...",
        ("Baseline mismatch",),
        ("baseline", "mismatch", "patch"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.UPDATE,
        "upgrade_failure",
        1603,
        "ERROR: In-place upgrade failed — rollback initiated.",
        "Upgrading from v1.0 to v2.0...",
        ("Upgrade failure",),
        ("upgrade", "failed"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.UPDATE,
        "rollback_failure",
        1603,
        "ERROR: Post-update rollback failed — system in inconsistent state.",
        "Rolling back failed update...",
        ("Rollback failure",),
        ("rollback", "failed"),
    )
)

# --- Category 16: Uninstallation ---
_register(
    FailureTemplate(
        FailureCategory.UNINSTALLATION,
        "missing_uninstall_cache",
        1603,
        "ERROR: Windows Installer uninstall cache entry missing.",
        "Locating uninstall information...",
        ("Missing uninstall cache",),
        ("uninstall", "cache", "missing"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.UNINSTALLATION,
        "shared_dependency_conflict",
        1603,
        "ERROR: Shared dependency still in use by another product.",
        "Checking shared dependencies...",
        ("Shared dependency conflict",),
        ("shared", "dependency", "conflict"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.UNINSTALLATION,
        "corrupt_uninstall_metadata",
        1603,
        "ERROR: Uninstall metadata corrupted in registry.",
        "Reading uninstall registry...",
        ("Corrupt uninstall metadata",),
        ("uninstall", "metadata", "corrupt"),
    )
)

# --- Category 17: Migration ---
_register(
    FailureTemplate(
        FailureCategory.MIGRATION,
        "profile_migration_corruption",
        1603,
        "ERROR: User profile migration data corrupted.",
        "Migrating user profile settings...",
        ("Profile migration corruption",),
        ("migration", "profile", "corruption"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.MIGRATION,
        "legacy_plugin_conflict",
        1603,
        "ERROR: Legacy plugin incompatible with migrated configuration.",
        "Migrating legacy plugins...",
        ("Legacy plugin conflict",),
        ("legacy", "plugin", "migration"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.MIGRATION,
        "config_migration_failure",
        1603,
        "ERROR: Configuration migration failed — settings file invalid.",
        "Migrating configuration...",
        ("Configuration migration failure",),
        ("configuration", "migration", "failed"),
    )
)

# --- Category 18: Localization ---
_register(
    FailureTemplate(
        FailureCategory.LOCALIZATION,
        "unicode_path_issue",
        1603,
        "ERROR: Unicode path not supported by installer engine.",
        "Installing to C:\\Users\\用户\\TestApp...",
        ("Unicode path issue",),
        ("unicode", "path", "localization"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.LOCALIZATION,
        "regional_settings_conflict",
        1603,
        "ERROR: Regional settings conflict (decimal separator).",
        "Applying locale-specific settings...",
        ("Regional settings conflict",),
        ("regional", "locale", "settings"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.LOCALIZATION,
        "non_english_path_failure",
        1603,
        "ERROR: Non-ASCII characters in installation path.",
        "Validating path encoding...",
        ("Non-English path failure",),
        ("path", "encoding", "non-ascii"),
    )
)

# --- Category 19: Plugin Ecosystem ---
_register(
    FailureTemplate(
        FailureCategory.PLUGIN_ECOSYSTEM,
        "plugin_api_mismatch",
        1603,
        "ERROR: Plugin API version mismatch (expected v3, found v2).",
        "Loading plugins...",
        ("Plugin API mismatch",),
        ("plugin", "API", "mismatch"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.PLUGIN_ECOSYSTEM,
        "binary_incompatibility",
        1603,
        "ERROR: Plugin binary incompatible with host application.",
        "Validating plugin binaries...",
        ("Binary incompatibility",),
        ("binary", "incompatible", "plugin"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.PLUGIN_ECOSYSTEM,
        "missing_plugin_dependency",
        1603,
        "ERROR: Plugin dependency libplugin_core.dll not found.",
        "Resolving plugin dependencies...",
        ("Missing plugin dependency",),
        ("plugin", "dependency", "missing"),
    )
)

# --- Category 20: Human/User ---
_register(
    FailureTemplate(
        FailureCategory.HUMAN_USER,
        "user_cancellation",
        1602,
        "ERROR: Installation cancelled by user.",
        "Waiting for user confirmation...",
        ("User cancelled", "Installation cancelled"),
        ("cancelled", "user", "abort"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.HUMAN_USER,
        "interrupted_installation",
        1603,
        "ERROR: Installation interrupted — process terminated.",
        "Installing components (step 3 of 5)...",
        ("Interrupted installation",),
        ("interrupted", "terminated"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.HUMAN_USER,
        "manual_file_deletion",
        1603,
        "ERROR: Required installation file deleted during setup.",
        "Verifying installation files...",
        ("Manual file deletion", "File not found"),
        ("deleted", "missing", "file"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.HUMAN_USER,
        "network_disconnect",
        1603,
        "ERROR: Network disconnected during online installation.",
        "Downloading additional components...",
        ("Network disconnected",),
        ("network", "disconnect"),
    )
)

# --- Category 21: Telemetry ---
_register(
    FailureTemplate(
        FailureCategory.TELEMETRY,
        "missing_logs",
        1603,
        "ERROR: Diagnostic log file missing — cannot continue verification.",
        "Writing diagnostic logs...",
        ("Missing logs",),
        ("logs", "missing", "diagnostic"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.TELEMETRY,
        "corrupted_diagnostics",
        1603,
        "ERROR: Diagnostic data corrupted.",
        "Collecting diagnostics...",
        ("Corrupted diagnostics",),
        ("diagnostics", "corrupted"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.TELEMETRY,
        "logging_service_failure",
        1603,
        "ERROR: Logging service failed to start.",
        "Starting telemetry logging service...",
        ("Logging service failure",),
        ("logging", "service", "failed"),
    )
)

# --- Category 22: Rare Edge Cases ---
_register(
    FailureTemplate(
        FailureCategory.RARE_EDGE_CASE,
        "certificate_expiration",
        1603,
        "ERROR: Code signing certificate expired.",
        "Verifying digital signature...",
        ("Certificate expired", "Signature invalid"),
        ("certificate", "expired", "signature"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.RARE_EDGE_CASE,
        "dst_timezone_issue",
        1603,
        "ERROR: DST/timezone transition caused timestamp validation failure.",
        "Validating installation timestamp...",
        ("DST timezone issue",),
        ("timezone", "DST", "timestamp"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.RARE_EDGE_CASE,
        "race_condition",
        1603,
        "ERROR: Race condition — concurrent file access conflict.",
        "Synchronizing installation steps...",
        ("Race condition",),
        ("race", "condition", "concurrent"),
    )
)
_register(
    FailureTemplate(
        FailureCategory.RARE_EDGE_CASE,
        "multi_process_sync",
        1603,
        "ERROR: Multi-process synchronization failure.",
        "Coordinating installer processes...",
        ("Multi-process synchronization",),
        ("synchronization", "multi-process"),
    )
)


def severity_multiplier(severity: FailureSeverity) -> int:
    return {
        FailureSeverity.LOW: 1,
        FailureSeverity.MEDIUM: 2,
        FailureSeverity.HIGH: 3,
        FailureSeverity.CRITICAL: 4,
    }[severity]
