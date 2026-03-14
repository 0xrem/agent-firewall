# 1.1.0 Release Readiness

This file records the release-readiness state for `1.1.0`.

## Release Position

`main` is being prepared as `1.1.0`, an adapter-contract hardening release.

That means:

- the official supported public surface remains intentionally narrow
- `agentfirewall.langgraph` remains the only official adapter contract
- preview runtime support is now documented for `agentfirewall.openai_agents` and `agentfirewall.generic`
- runtime support inventory and packaged local evidence can now be exported as JSON

It does not mean:

- a second official runtime adapter
- full OpenAI Agents feature coverage
- hosted OpenAI tools, MCP servers, or handoffs
- a reviewer UI or centralized approval service

## Supported Contract

The official supported `1.1.0` path is:

- `agentfirewall` for core firewall construction
- `agentfirewall.langgraph` for the official LangGraph runtime path
- `agentfirewall.approval` for documented deterministic approval helpers

The documented preview runtime paths are:

- `agentfirewall.openai_agents` for the function_tool-first OpenAI Agents candidate path
- `agentfirewall.generic` for low-level guarded wrappers on unsupported runtimes
- `agentfirewall.runtime_support` for exporting support inventory and evidence as JSON

See [SUPPORTED_PATH.md](./SUPPORTED_PATH.md) for the import-level contract.

## Validation Snapshot

Validated locally from a repository checkout on the current development environment.

Commands:

```bash
source venv/bin/activate
python examples/attack_scenarios.py
python examples/langgraph_quickstart.py
python examples/langgraph_agent.py
python examples/langgraph_trial_run.py
python examples/generic_tool_dispatcher.py
python examples/openai_agents_quickstart.py
python examples/openai_agents_demo.py
python -m agentfirewall.evals.langgraph
python -m agentfirewall.evals.generic
python -m agentfirewall.evals.openai_agents
python -m agentfirewall.runtime_support --include-evidence --output docs/assets/runtime-support-manifest.json
python -m pytest tests/ -q
python -m build --no-isolation
python -m twine check dist/agentfirewall-1.1.0.tar.gz dist/agentfirewall-1.1.0-py3-none-any.whl
```

Observed results:

- 6 attack scenarios run with full audit trails
- local LangGraph quick start runs on the official supported path with guarded tools
- local LangGraph demo exercises review, approval, and guarded side effects
- local trial runner covers 10 task-oriented LangGraph workflows
- local generic preview example runs on the shared low-level wrappers
- local OpenAI Agents quick start and demo run without hosted OpenAI services
- packaged LangGraph eval suite covers 19 task-oriented cases and passes `19/19`
- packaged generic preview eval suite covers 7 local cases and passes `7/7`
- packaged OpenAI Agents preview eval suite covers 9 local cases and passes `9/9`
- runtime support manifest exports official adapter inventory, preview runtime inventory, capability matrix, and packaged evidence
- 149 unit and integration tests pass locally
- sdist and wheel build cleanly
- `twine check` passes for the `1.1.0` artifacts

## Why This Is 1.1.0

The current repo state has:

- one documented and supported official adapter with full guarded-tool coverage
- a deliberate adapter SPI with conformance and release-gate machinery in-repo
- documented preview runtime support for OpenAI Agents SDK and generic wrappers
- repeatable local evidence for LangGraph, generic wrappers, and OpenAI Agents preview paths
- a machine-readable runtime support manifest for docs, dashboards, and sites
- a narrow enough official public API to carry forward without surface resets

## Known Limits

- the only official adapter contract is still LangGraph
- OpenAI Agents is preview-only and scoped to the documented function_tool-first boundary
- generic wrappers are preview support, not an official adapter
- the current evidence path is local and fake-model-based
- false-positive tuning will still benefit from user feedback

## Publish Checklist

- [x] Version metadata set to `1.1.0`
- [x] Supported contract documented
- [x] Preview runtime boundaries documented
- [x] Release-readiness notes updated
- [x] README updated with current `1.1.0` promise
- [x] Runtime support manifest exported
- [x] LangGraph validation path re-run
- [x] Generic preview validation path run
- [x] OpenAI Agents preview validation path run
- [x] Test suite green locally
- [x] Build and `twine check` green
