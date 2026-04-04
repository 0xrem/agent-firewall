# Who Should Use AgentFirewall Now

This page is intentionally direct. It is here to reduce confusion between what AgentFirewall supports today and what is only on the roadmap.

## Good Fit Right Now

You should try AgentFirewall now if:

- you have a Python agent that can call shell, file, HTTP, or custom tools
- you are on LangGraph and want an official adapter path
- you are on the OpenAI Agents SDK and your integration is still inside the documented `function_tool`-first boundary
- you want a pre-execution security layer that can start in `log-only`
- you are on an unsupported runtime but can test with low-level guarded wrappers first

## Not A Good Fit Right Now

You should probably wait if you need:

- hosted OpenAI tools as part of the supported contract
- MCP client or server support as a supported contract
- handoffs as part of the official adapter promise
- a reviewer UI, control plane, or hosted approval service
- non-Python runtime support as a first-class product path today

## If You Are On An Unsupported Runtime

Start with the preview generic wrapper path:

```python
from agentfirewall import FirewallConfig
from agentfirewall.generic import create_generic_runtime_bundle

bundle = create_generic_runtime_bundle(
    config=FirewallConfig(name="generic-preview"),
)
```

Use that path to answer three questions quickly:

- do your tool calls map cleanly onto guarded shell, file, and HTTP surfaces?
- which events would immediately show up in `log-only`?
- which runtime-specific pieces would still need a future official adapter?

The generic path is a preview fallback, not a promise that every runtime is already supported.

## If You Need Hosted Tools, MCP, Or Handoffs

AgentFirewall is not the right production promise for that today.

Why:

- hosted OpenAI tools are outside the current official support boundary
- MCP work is still a thin-core roadmap item, not a `1.2.0` feature contract
- handoffs are not part of the documented OpenAI Agents adapter scope

If those are mandatory requirements, wait for a later release instead of assuming the current preview direction is already supported.

## Recommended Starting Order

If you are a fit today:

1. Run [`../../examples/attack_scenarios.py`](../../examples/attack_scenarios.py).
2. Move to [`LOG_ONLY_ROLLOUT.md`](./LOG_ONLY_ROLLOUT.md).
3. Wire the official adapter or generic preview path that matches your runtime.

## Related Docs

- first-run path: [`QUICKSTART_60S.md`](./QUICKSTART_60S.md)
- rollout guide: [`LOG_ONLY_ROLLOUT.md`](./LOG_ONLY_ROLLOUT.md)
- supported contract: [`../alpha/SUPPORTED_PATH.md`](../alpha/SUPPORTED_PATH.md)
