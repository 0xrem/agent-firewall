"""Subprocess execution helpers guarded by AgentFirewall."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Callable

from ..events import EventContext
from ..firewall import AgentFirewall


@dataclass(slots=True)
class GuardedSubprocessRunner:
    """Evaluate subprocess execution before delegating to a real runner."""

    firewall: AgentFirewall
    runner: Callable[..., Any] = field(default=subprocess.run)
    source: str = "agent"

    def run(
        self,
        command: str | Sequence[str],
        *,
        shell: bool = False,
        **kwargs: Any,
    ) -> Any:
        event = EventContext.command(
            command,
            shell=shell,
            cwd=kwargs.get("cwd"),
            source=self.source,
        )
        self.firewall.enforce(event)
        return self.runner(command, shell=shell, **kwargs)
