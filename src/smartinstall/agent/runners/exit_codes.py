"""Known MSI / installer exit code mappings (functional-spec §2.2)."""

from __future__ import annotations

MSI_EXIT_CODES: dict[int, str] = {
    0: "Success",
    1602: "User cancelled installation",
    1603: "Fatal error during installation",
    1618: "Another installation is already in progress",
    1619: "Installation package could not be opened",
    1620: "Installation package is invalid",
    1638: "Another version of this product is already installed",
    1402: "Could not open key (access denied)",
    1406: "Could not write value to registry",
}


def describe_exit_code(exit_code: int) -> tuple[str, bool]:
    description = MSI_EXIT_CODES.get(exit_code)
    if description is not None:
        return description, True
    return f"Unknown exit code ({exit_code})", False
