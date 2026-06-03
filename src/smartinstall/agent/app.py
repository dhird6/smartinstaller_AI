"""CLI with subcommands: run, run-all, install, recover, demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from smartinstall.agent.di.container import ServiceContainer, build_container
from smartinstall.agent.orchestration.automated_run_orchestrator import AutomatedRunResult, BatchRunResult
from smartinstall.agent.slm.auto_diagnosis import run_slm_for_report
from smartinstall.core.models.requests import StartSessionRequest
from smartinstall.core.models.unified_report import UnifiedInstallationReport

_SUBCOMMANDS = frozenset({"run", "run-all", "install", "recover", "demo", "gui", "service"})


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smartinstall",
        description="SmartInstall AI — One-command monitored installation",
    )
    parser.add_argument("--config", dest="config_path", help="Path to smartinstall.config.json")

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    run_parser = subparsers.add_parser(
        "run",
        help="Discover installer from installers/ and run full workflow (default)",
    )
    _add_run_options(run_parser)

    run_all_parser = subparsers.add_parser(
        "run-all",
        help="Run all installers in installers/ sequentially",
    )
    _add_run_options(run_all_parser)
    run_all_parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop batch when an installation fails",
    )

    install_parser = subparsers.add_parser(
        "install",
        help="Run monitored install using an explicit installer path",
    )
    install_parser.add_argument("installer_path", help="Absolute path to installer")
    install_parser.add_argument("--type", choices=["EXE", "MSI"], dest="installer_type")
    install_parser.add_argument("--product-name", dest="product_name")
    install_parser.add_argument("--product-version", dest="product_version")
    install_parser.add_argument("--tag", dest="caller_tag")
    install_parser.add_argument("--args", dest="additional_args")
    install_parser.add_argument("--timeout", type=int, dest="timeout_seconds")

    subparsers.add_parser("gui", help="Launch desktop chat application")
    service_parser = subparsers.add_parser(
        "service",
        help="Windows SCM service control (install/start/stop/remove)",
    )
    service_parser.add_argument(
        "service_command",
        choices=["install", "remove", "start", "stop", "restart"],
        help="Service control action (requires Administrator on Windows)",
    )
    subparsers.add_parser("recover", help="Mark incomplete sessions as Incomplete")
    demo_parser = subparsers.add_parser("demo", help="Foundation demo without installer launch")
    demo_parser.add_argument("installer_path", nargs="?", help="Optional installer path")
    demo_parser.add_argument("--simulate-exit-code", type=int, default=0)

    return parser


def _add_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--installer",
        dest="installer_name",
        help="Specific installer file name in installers/ (default: newest file)",
    )
    parser.add_argument("--product-name", dest="product_name")
    parser.add_argument("--tag", dest="caller_tag")
    parser.add_argument("--args", dest="additional_args", help="Installer arguments (quoted)")
    parser.add_argument("--timeout", type=int, dest="timeout_seconds")


def run(argv: list[str] | None = None) -> int:
    parser = create_argument_parser()
    args = parser.parse_args(argv)

    command = args.command
    if command is None:
        command = "run"

    config_path = Path(args.config_path).resolve() if getattr(args, "config_path", None) else None
    container = build_container(config_path)

    if command == "gui":
        return _run_desktop(config_path)

    if command == "recover":
        count = container.session_manager.recover_incomplete_sessions()
        container.logger.info("recover_only_complete", count=count)
        return 0

    if command == "demo":
        return _run_foundation_demo(container, args)

    if command == "run":
        return _run_automated(container, args)

    if command == "run-all":
        return _run_all_automated(container, args)

    if command == "install":
        return _run_explicit_install(container, args)

    if command == "service":
        return _run_service_command(args.service_command)

    parser.print_help()
    return 4


def _run_automated(container: ServiceContainer, args: argparse.Namespace) -> int:
    from smartinstall.agent.infrastructure.privilege_checker import (
        admin_status_message,
        is_user_admin,
    )

    privilege_msg = admin_status_message()
    container.logger.info("privilege_check", message=privilege_msg)
    if not is_user_admin():
        print(privilege_msg)
        print("If a UAC dialog appears, click Yes to allow the installer to run.\n")

    result = container.automated_run_orchestrator.run(
        installer_name=getattr(args, "installer_name", None),
        product_name=getattr(args, "product_name", None),
        caller_tag=getattr(args, "caller_tag", None),
        additional_args=getattr(args, "additional_args", None),
        timeout_seconds=getattr(args, "timeout_seconds", None),
    )
    if not result.success or result.value is None:
        container.logger.error("automated_run_failed", error=result.error)
        return _map_error_to_exit_code(result.error.error_code if result.error else "")

    value = result.value
    _log_run_complete(container, value)
    _run_slm_diagnosis(container, value.report_path)
    return _map_workflow_status_to_exit(value.workflow_status)


def _run_all_automated(container: ServiceContainer, args: argparse.Namespace) -> int:
    result = container.automated_run_orchestrator.run_all(
        caller_tag=getattr(args, "caller_tag", None),
        additional_args=getattr(args, "additional_args", None),
        timeout_seconds=getattr(args, "timeout_seconds", None),
        stop_on_failure=getattr(args, "stop_on_failure", False),
    )
    if not result.success or result.value is None:
        container.logger.error("run_all_failed", error=result.error)
        return _map_error_to_exit_code(result.error.error_code if result.error else "")

    batch: BatchRunResult = result.value
    container.logger.info(
        "run_all_complete",
        total=len(batch.runs),
        failures=batch.failures,
    )
    for run_item in batch.runs:
        _log_run_complete(container, run_item)
        _run_slm_diagnosis(container, run_item.report_path)

    return 0 if batch.failures == 0 else 1


def _run_explicit_install(container: ServiceContainer, args: argparse.Namespace) -> int:
    request = StartSessionRequest(
        installerPath=args.installer_path,
        installerType=args.installer_type,
        productName=args.product_name,
        productVersion=getattr(args, "product_version", None),
        callerTag=args.caller_tag,
        outputDirectory=str(container.config.output_root),
        additionalArgs=args.additional_args,
        timeoutSeconds=args.timeout_seconds,
    )
    install_result = container.installation_agent.run_monitored_installation(request)
    if not install_result.success or install_result.value is None:
        container.logger.error("install_failed", error=install_result.error)
        return _map_error_to_exit_code(
            install_result.error.error_code if install_result.error else ""
        )

    session, unified = install_result.value
    report_path = container.automated_run_orchestrator._publisher.publish(  # noqa: SLF001
        unified,
        application_name=args.product_name or Path(args.installer_path).stem,
    )
    _print_report_summary(report_path, unified)
    _run_slm_diagnosis(container, report_path)
    return _map_workflow_status_to_exit(unified.status.installation_outcome)


def _log_run_complete(container: ServiceContainer, value: AutomatedRunResult) -> None:
    container.logger.info(
        "workflow_complete",
        installer=value.discovered.file_name,
        session_id=value.session.session_id,
        status=value.workflow_status,
        report=str(value.report_path),
        error_count=len(value.report.errors),
        artifacts=value.session.output_directory,
    )
    _print_report_summary(value.report_path, value.report)


def _print_report_summary(report_path: Path, report: UnifiedInstallationReport) -> None:
    print(f"Installer:  {report.status.installer.installer_name}")
    print(f"Status:     {report.status.installation_outcome}")
    print(f"Completed:  {report.status.installation_completed}")
    print(f"Report:     {report_path}")
    print(f"Errors:     {len(report.errors)} item(s) — see 'errors' section in report JSON")
    if report.errors:
        print("Top error:")
        top = report.errors[0]
        print(f"  [{top.category}] {top.message[:200]}")
    print(f"Logs:       {report.status.artifact_directory}")


def _run_slm_diagnosis(container: ServiceContainer, report_path: Path) -> None:
    container.logger.info("slm_autorun_started", report=str(report_path))
    result = run_slm_for_report(report_path)
    if not result.success:
        container.logger.warning(
            "slm_autorun_failed",
            report=str(report_path),
            error=result.error,
            return_code=result.return_code,
        )
        return

    container.logger.info(
        "slm_autorun_complete",
        report=str(report_path),
        return_code=result.return_code,
    )
    print("\nSLM Diagnosis:")
    print(result.output or "(no output)")


def _run_service_command(action: str) -> int:
    import sys

    if sys.platform != "win32":
        print("Windows Service commands require Windows.", file=sys.stderr)
        return 3

    from smartinstall.agent.windows.monitor_windows_service import handle_service_command_line

    sys.argv = ["smartinstall", "service", action]
    handle_service_command_line()
    return 0


def _run_desktop(config_path: Path | None) -> int:
    try:
        from smartinstall.ui.main import run_desktop
    except ImportError as exc:
        print(
            "Desktop dependencies are missing. Install with:\n"
            "  pip install -e \".[desktop]\""
        )
        return 3
    return run_desktop(config_path)


def _run_foundation_demo(container: ServiceContainer, args: argparse.Namespace) -> int:
    installer_path = getattr(args, "installer_path", None)
    if not installer_path:
        demo_installer = Path(r"C:\Temp\demo_setup.exe")
        demo_installer.parent.mkdir(parents=True, exist_ok=True)
        if not demo_installer.exists():
            demo_installer.write_bytes(b"")
        installer_path = str(demo_installer)

    request = StartSessionRequest(
        installerPath=installer_path,
        productName="Foundation Demo",
        outputDirectory=str(container.config.output_root),
    )
    result = container.session_manager.run_foundation_lifecycle(
        request,
        simulate_exit_code=getattr(args, "simulate_exit_code", 0),
    )
    if not result.success:
        return 3
    return 0 if getattr(args, "simulate_exit_code", 0) == 0 else 1


def _map_workflow_status_to_exit(status: str) -> int:
    normalized = status.lower()
    if normalized == "success":
        return 0
    if normalized == "crashed":
        return 2
    if normalized in {"failure", "timedout", "timed_out", "partial"}:
        return 1
    return 3


def _map_error_to_exit_code(error_code: str) -> int:
    if error_code == "SESSION_INSUFFICIENT_PRIVILEGES":
        return 5
    if error_code in {"SESSION_INVALID_INPUT", "SESSION_INSTALLER_NOT_FOUND", "NO_INSTALLERS_FOUND"}:
        return 4
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
