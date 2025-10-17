"""Optional helper utilities for interacting with native desktop applications."""
from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Iterable, List


class SecurityError(RuntimeError):
    """Raised when a disallowed operation is attempted."""


@dataclass
class NativeBridge:
    """Executes whitelisted desktop commands.

    The bridge is intentionally strict: commands must be registered in advance
    together with the exact executable and argument template to prevent
    arbitrary command execution.
    """

    allowlist: Dict[str, List[str]] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=lambda: dict(os.environ))

    def register(self, name: str, command: Iterable[str]) -> None:
        self.allowlist[name] = list(command)

    def is_allowed(self, name: str) -> bool:
        return name in self.allowlist

    def run(self, name: str, extra_args: Iterable[str] | None = None) -> subprocess.CompletedProcess[str]:
        if not self.is_allowed(name):
            raise SecurityError(f"Command '{name}' is not allowlisted")
        base_cmd = self.allowlist[name]
        args = list(base_cmd)
        if extra_args:
            for arg in extra_args:
                if arg.startswith("--unsafe"):
                    raise SecurityError("Arguments containing '--unsafe' are blocked")
                args.append(arg)
        return subprocess.run(args, env=self.environment, text=True, capture_output=True, check=True)

    def describe(self) -> Dict[str, List[str]]:
        return {name: list(cmd) for name, cmd in self.allowlist.items()}


def format_command(command: Iterable[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


__all__ = ["NativeBridge", "SecurityError", "format_command"]
