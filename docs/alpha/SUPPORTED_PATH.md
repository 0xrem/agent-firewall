# Supported Path

This document defines the supported API surface for AgentFirewall `1.1.0`.

It is narrower than the full package contents on purpose.

## Official Supported Imports

Use top-level `agentfirewall` for the runtime-agnostic core:

- `AgentFirewall`
- `FirewallConfig`
- `ApprovalResponse`
- `ReviewRequired`
- `FirewallViolation`
- `InMemoryAuditSink`
- `create_firewall(...)`

Use `agentfirewall.langgraph` for the supported runtime path:

- `create_agent(...)`
- `create_shell_tool(...)`
- `create_http_tool(...)`
- `create_file_reader_tool(...)`
- `create_file_writer_tool(...)`

Use `agentfirewall.approval` for the documented approval helper path:

- `StaticApprovalHandler`
- `approve_all(...)`
- `deny_all(...)`
- `timeout_all(...)`

Lower-level helpers under modules such as `agentfirewall.enforcers`, `agentfirewall.audit`, `agentfirewall.policy_packs`, and `agentfirewall.integrations.langgraph` are still useful, but they are advanced usage rather than the primary supported entrypoint.

## Documented Preview Runtime Paths

`1.1.0` also documents two preview runtime paths.

They are deliberately real enough to evaluate locally, but they are not part of the official adapter contract yet.

### Preview Runtime: OpenAI Agents SDK

The repo contains an experimental OpenAI Agents SDK path under `agentfirewall.openai_agents`:

```python
from agentfirewall import FirewallConfig, create_firewall
from agentfirewall.openai_agents import create_agent, create_shell_tool

firewall = create_firewall(
    config=FirewallConfig(name="demo"),
)

shell_tool = create_shell_tool(firewall=firewall)

agent = create_agent(
    agent=your_openai_agent,
    firewall=firewall,
)
```

Current boundary:

- function-tool-first only
- local helper tools and a `create_runtime_bundle(...)` entrypoint exist for shell, file, and HTTP
- packaged local evals are available under `python -m agentfirewall.evals.openai_agents`
- hosted tools, MCP servers, and handoffs are still out of scope
- this path is not yet part of the official supported adapter contract

Install with:

```bash
python -m pip install agentfirewall[openai-agents]
```

### Preview Runtime: Generic Wrappers

The repo also contains a low-level guarded wrapper path under `agentfirewall.generic`:

```python
from agentfirewall import FirewallConfig
from agentfirewall.generic import create_generic_runtime_bundle

bundle = create_generic_runtime_bundle(
    config=FirewallConfig(name="generic-preview"),
)
```

Current boundary:

- intended for unsupported tool-calling runtimes
- prompt inspection is not provided on this path
- shell, file, and HTTP enforcement are available through shared guarded wrappers
- packaged local evals are available under `python -m agentfirewall.evals.generic`
- this path is preview runtime support, not an official adapter contract

### Runtime Support Inventory

For docs, dashboards, or sites, the repo also exposes a machine-readable support snapshot:

```bash
python -m agentfirewall.runtime_support --include-evidence
```

This exports the current official adapter inventory, preview runtime inventory, capability matrix, and packaged local evidence as JSON.

## Install

```bash
python -m pip install -U pip
python -m pip install agentfirewall[langgraph]
```

For local repo development:

```bash
python -m pip install -e '.[langgraph,openai-agents]'
```

## Minimal Quick Start

```python
from agentfirewall import FirewallConfig, create_firewall
from agentfirewall.langgraph import create_agent, create_shell_tool

firewall = create_firewall(
    config=FirewallConfig(name="demo"),
)

shell_tool = create_shell_tool(firewall=firewall)

agent = create_agent(
    model=model,
    tools=[status_tool, shell_tool],
    firewall=firewall,
)
```

This keeps one explicit firewall instance across:

- prompt inspection in LangGraph middleware
- tool-call review or blocking
- guarded shell execution inside the official shell tool
- audit recording for each decision
- runtime-context correlation from guarded side effects back to the originating tool call

## Approval Path

By default, a `review` decision raises `ReviewRequired` on enforced surfaces.

The documented path for local demos, evals, and simple integrations is `StaticApprovalHandler`:

```python
from agentfirewall import ApprovalResponse, FirewallConfig, create_firewall
from agentfirewall.approval import StaticApprovalHandler
from agentfirewall.langgraph import create_agent, create_shell_tool

approval = StaticApprovalHandler(
    default="timeout",
    tool_outcomes={
        "shell": ApprovalResponse.approve(
            reason="Approved for local development."
        )
    },
    metadata={"approval_path": "local-static-review"},
)

firewall = create_firewall(
    config=FirewallConfig(name="demo"),
    approval_handler=approval,
)

agent = create_agent(
    model=model,
    tools=[create_shell_tool(firewall=firewall)],
    firewall=firewall,
)
```

The matching order is:

1. exact tool name for `tool_call` events
2. event kind such as `prompt` or `http_request`
3. the default outcome

Custom approval callbacks are still supported, but `StaticApprovalHandler` is the recommended helper because it is deterministic and easy to verify in demos and evals.

## Local Validation Commands

```bash
source venv/bin/activate
python examples/attack_scenarios.py
python examples/langgraph_quickstart.py
python examples/langgraph_agent.py
python examples/langgraph_trial_run.py
python -m agentfirewall.evals.langgraph
python -m agentfirewall.evals.generic
python -m agentfirewall.evals.openai_agents
python -m agentfirewall.runtime_support --include-evidence
python -m pytest tests/ -v
```

The trial runner and eval runner both emit ordered traces. For guarded shell, HTTP, and file events, those traces include `runtime_context` metadata such as the originating `tool_name` and `tool_call_id`.

The per-scenario audit summaries also include:

- `source_counts`
- `tool_name_counts`
- task-oriented workflow labels in the emitted JSON payloads

For docs, dashboards, or the GitHub Pages site, you can also export the current support inventory and packaged evidence as JSON:

```bash
python -m agentfirewall.runtime_support --include-evidence
```

For `log-only` flows, trace entries preserve `decision_metadata.original_action` so a user can see whether a step would have been reviewed or blocked before turning on enforcement.

The packaged LangGraph eval suite covers 19 task-oriented local cases, the generic preview suite covers 7 local cases, and the OpenAI Agents preview suite covers 9 local cases.

## What This Contract Does Not Promise Yet

- a built-in reviewer UI
- a centralized approval service
- a second officially supported runtime adapter
- hosted OpenAI tools, MCP servers, or handoffs
- production-ready false-positive tuning
