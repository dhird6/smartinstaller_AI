@echo off
REM QA: long-running fake installer for testing live monitoring + injected errors.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_slow_test_installer.ps1" -Seconds 45
