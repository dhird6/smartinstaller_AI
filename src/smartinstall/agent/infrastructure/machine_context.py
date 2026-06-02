"""Machine context capture for session metadata (functional-spec §1.4)."""

from __future__ import annotations

import getpass
import os
import platform
import socket
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MachineContext:
    machine_name: str
    os_version: str
    os_build: str
    architecture: str
    current_user: str


def capture_machine_context() -> MachineContext:
    arch = platform.machine().upper()
    if arch in {"AMD64", "X86_64"}:
        architecture = "x64"
    elif arch in {"X86", "I386"}:
        architecture = "x86"
    elif "ARM" in arch:
        architecture = "ARM64"
    else:
        architecture = "x64"

    username = getpass.getuser()
    domain = os.environ.get("USERDOMAIN", "")
    current_user = f"{domain}\\{username}" if domain else username

    return MachineContext(
        machine_name=socket.gethostname(),
        os_version=platform.platform(),
        os_build=platform.version(),
        architecture=architecture,
        current_user=current_user,
    )
