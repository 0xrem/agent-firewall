"""HTTP helpers guarded by AgentFirewall."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.request import Request, urlopen

from ..events import EventContext
from ..firewall import AgentFirewall


@dataclass(slots=True)
class GuardedHttpClient:
    """Evaluate outbound requests before delegating to an opener."""

    firewall: AgentFirewall
    opener: Callable[..., Any] = field(default=urlopen)
    source: str = "agent"

    def request(
        self,
        url: str,
        *,
        method: str = "GET",
        **kwargs: Any,
    ) -> Any:
        event = EventContext.http_request(url, method=method, source=self.source)
        self.firewall.enforce(event)

        headers = kwargs.pop("headers", None) or {}
        data = kwargs.pop("data", None)
        request = Request(url=url, data=data, headers=headers, method=method.upper())
        return self.opener(request, **kwargs)
