# 1.2.0 Release Readiness

This file records the release-readiness state for `1.2.0`.

## Release Position

`main` is being prepared as `1.2.0`, the multi-runtime proof release.

That means:

- the official supported public surface now includes two adapters
- `agentfirewall.langgraph` remains an official adapter contract
- `agentfirewall.openai_agents` is now the second official adapter contract
- `agentfirewall.generic` remains the preview runtime path
- `agentfirewall.mcp` is only an experimental local preview path, not an official adapter contract
- runtime support inventory and packaged local evidence export as JSON

It does not mean:

- full OpenAI Agents feature coverage
- hosted OpenAI tools, MCP servers, or handoffs
- a reviewer UI or centralized approval service
- production-grade false-positive tuning for unknown workloads

## Supported Contract

The official supported `1.2.0` path is:

- `agentfirewall` for core firewall construction
- `agentfirewall.langgraph` for the official LangGraph runtime path
- `agentfirewall.openai_agents` for the official OpenAI Agents runtime path
- `agentfirewall.approval` for documented deterministic approval helpers

The documented preview runtime paths are:

- `agentfirewall.generic` for low-level guarded wrappers on unsupported runtimes
- `agentfirewall.mcp` for experimental local MCP client/server loopback preview bundles
- `agentfirewall.runtime_support` for exporting support inventory and evidence as JSON

See [SUPPORTED_PATH.md](./SUPPORTED_PATH.md) for the import-level contract.

## Validation Snapshot

Validated locally from a repository checkout on the current development environment.

Commands run:

```bash
source venv/bin/activate
python examples/attack_scenarios.py
python examples/langgraph_quickstart.py
python examples/langgraph_trial_run.py
python examples/generic_preview_demo.py
python examples/openai_agents_quickstart.py
python examples/openai_agents_demo.py
python -m agentfirewall.evals.langgraph
python -m agentfirewall.evals.generic
python -m agentfirewall.evals.openai_agents
python -m agentfirewall.evals.mcp_client
python -m agentfirewall.evals.mcp_server
python -m agentfirewall.runtime_support --include-evidence --output docs/assets/runtime-support-manifest.json
python -m unittest discover -s tests -q
python -m build --no-isolation
python -m twine check dist/agentfirewall-1.2.0.tar.gz dist/agentfirewall-1.2.0-py3-none-any.whl
```

Observed results:

- attack-scenario demo runs with full audit trails
- LangGraph quickstart runs locally without an API key
- LangGraph trial runner emits 10 task-oriented workflow traces
- generic preview example runs on the shared low-level wrappers
- OpenAI Agents quickstart and demo run locally without hosted OpenAI services
- packaged LangGraph eval suite covers 19 task-oriented cases and passes `19/19`
- packaged generic preview eval suite covers 9 local cases and passes `9/9`
- packaged OpenAI Agents official eval suite covers 11 local cases and passes `11/11`
- packaged MCP client preview eval suite covers 8 local cases and passes `8/8`
- packaged MCP server preview eval suite covers 6 local cases and passes `6/6`
- runtime support manifest exports 2 official adapters, 3 preview runtimes, capability rows, and packaged evidence
- `unittest` passes for the packaged local test suite in the repo environment
- sdist and wheel build cleanly
- `twine check` passes for the `1.2.0` artifacts

## Why This Is 1.2.0

The current repo state has:

- two documented and release-gated official adapters
- one documented generic preview runtime path plus experimental local MCP client/server preview paths
- a deliberate adapter SPI with shared conformance and release-gate machinery in-repo
- repeatable local evidence for LangGraph, OpenAI Agents, generic wrappers, and experimental local MCP loopback previews
- a machine-readable runtime support manifest for docs, dashboards, and sites
- a narrow enough official public API to carry forward without surface resets

## Known Limits

- OpenAI Agents support is intentionally scoped to the documented `function_tool`-first boundary
- hosted tools, MCP servers, handoffs, and `Agent.as_tool()` remain out of scope
- generic wrappers are still preview support, not an official adapter
- MCP loopback bundles are experimental local preview only, not official adapter support
- the current evidence path is local and fake-model-based
- false-positive tuning will still benefit from user feedback

## Publish Checklist

- [x] Version metadata set to `1.2.0`
- [x] Supported contract documented
- [x] OpenAI Agents promotion reflected in official adapter registry
- [x] Preview runtime boundaries documented
- [x] Release-readiness notes updated
- [x] README updated with current `1.2.0` promise
- [x] Runtime support manifest exported
- [x] LangGraph validation path re-run
- [x] Generic preview validation path run
- [x] OpenAI Agents validation path run
- [x] Test suite green locally
- [x] Build and `twine check` green
