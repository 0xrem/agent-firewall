# OpenAI Agents Adapter Plan

## Purpose

This document explains how AgentFirewall should turn the current OpenAI Agents SDK skeleton into a real second-adapter candidate without drifting away from the main product goal.

The goal is not to support every OpenAI Agents feature immediately.

The goal is to prove that the shared runtime firewall core can protect a second agent runtime while preserving the same policy semantics, review behavior, audit shape, and runtime-context correlation already established by LangGraph.

## Current State

The repo already contains an experimental OpenAI Agents SDK adapter skeleton:

- [`src/agentfirewall/integrations/openai_agents.py`](../../src/agentfirewall/integrations/openai_agents.py)
- [`src/agentfirewall/openai_agents.py`](../../src/agentfirewall/openai_agents.py)
- [`tests/test_openai_agents_integration.py`](../../tests/test_openai_agents_integration.py)

What already works:

- prompt inspection through agent hooks before the model runs
- function-tool interception before local tool execution
- AgentFirewall `review` and `log-only` semantics on function tools
- nested runtime-context propagation when a wrapped function tool calls shared enforcers like `GuardedSubprocessRunner`
- local smoke tests using a fake model, with no network calls and no API key required

What is not done yet:

- packaged OpenAI eval suite
- OpenAI-specific helper builders for shell, file, and HTTP
- release-gate expectations
- conformance and promotion decision for official-adapter status

## Why OpenAI Agents

OpenAI Agents is the right second-adapter candidate because it is different enough from LangGraph to prove adapter reuse, but still close enough to the current tool-calling execution model to reuse the same core firewall semantics.

It is a better near-term candidate than MCP because:

- it is smaller in scope
- it maps cleanly onto `prompt` and `tool_call`
- it lets us validate tool-triggered side effects without inventing new event kinds too early

It is a better near-term proof point than a LangChain adapter because:

- it demonstrates a genuinely different runtime shape
- it reduces the risk that the product still looks LangGraph-local even after `1.1`

## Support Boundary

`1.2` should remain intentionally narrow.

Supported in scope:

- OpenAI Agents SDK `Agent`
- local `FunctionTool`
- prompt inspection before model execution
- function-tool interception before execution
- shared `review` / `block` / `log-only` behavior
- runtime-context propagation into shared shell, file, and HTTP enforcers when tool bodies call them

Explicitly out of scope for this phase:

- hosted tools
- MCP servers
- handoffs
- `Agent.as_tool()`
- SDK-native `needs_approval` as the primary approval mechanism
- realtime agents

## Design Rules

### 1. Keep AgentFirewall As The Decision Authority

The adapter should keep using AgentFirewall as the place where `allow` / `block` / `review` / `log` decisions happen.

Do not split the semantics between:

- AgentFirewall review behavior
- OpenAI SDK `needs_approval`

For now, `needs_approval` should remain unsupported for wrapped tools. The adapter should rely on AgentFirewall review semantics instead.

### 2. Preserve Raw Firewall Exceptions

The adapter should avoid hiding AgentFirewall exceptions behind model-visible tool error strings.

That means:

- wrapped function tools should not silently convert `ReviewRequired` or `FirewallViolation` into normal tool outputs
- failure formatting should not override the firewall's decision semantics

### 3. Keep Prompt Inspection Lightweight

Prompt inspection should happen before model execution and should only inspect the current user input, not re-review stale turns on every loop iteration.

This keeps OpenAI Agents behavior aligned with the LangGraph prompt path.

### 4. Reuse Shared Enforcers

The adapter should not implement OpenAI-specific shell, file, or HTTP enforcement logic from scratch.

It should reuse:

- `GuardedSubprocessRunner`
- `GuardedFileAccess`
- `GuardedHttpClient`

The OpenAI-specific layer should only handle runtime translation and context propagation.

## Work Packages

## 1. Evidence Package

Ship:

- packaged local eval suite for OpenAI Agents
- local eval cases stored alongside LangGraph and generic cases
- fake-model runner so all evals remain offline and deterministic

Minimum case coverage:

- safe prompt with safe function tool
- prompt that triggers review before model execution
- safe tool call
- reviewed tool call without approval
- reviewed tool call with approval
- log-only function-tool workflow
- nested side-effect correlation through shell, file, or HTTP

Definition of done:

- OpenAI evals run locally with no API key
- expected counts are stable and machine-checkable

## 2. Helper Surface Package

Ship:

- `create_guarded_openai_agents_shell_tool(...)`
- `create_guarded_openai_agents_http_tool(...)`
- `create_guarded_openai_agents_file_reader_tool(...)`
- `create_guarded_openai_agents_file_writer_tool(...)`

Design constraints:

- helpers should create local `FunctionTool` instances
- helpers should reuse shared enforcers
- helpers should carry runtime-context metadata automatically

Definition of done:

- OpenAI helper tools have the same user-visible safety behavior as LangGraph helper tools on equivalent flows

## 3. Release Evidence Package

Ship:

- OpenAI eval expectations
- candidate release gate entrypoint
- runtime-support inventory updates
- capability row updates once helper surfaces are real

Important rule:

- do not add OpenAI Agents to the official adapter registry until the evidence package is complete

Definition of done:

- the repo can explain exactly what OpenAI Agents supports and can prove it with local evidence

## 4. Promotion Decision Package

Ship:

- a final go/no-go decision on whether OpenAI Agents becomes the second official adapter

Promotion criteria:

- packaged eval suite is stable
- helper surfaces for shell, file, and HTTP exist and are regression-covered
- review, log-only, and runtime-context semantics are preserved
- docs clearly state supported and unsupported paths

Definition of done:

- either OpenAI Agents is promoted into the official adapter registry, or it remains clearly labeled as an experimental candidate with explicit reasons

## Testing Strategy

OpenAI Agents work should be validated in four layers.

### 1. Adapter Unit Tests

Test:

- prompt translator behavior
- function-tool wrapper behavior
- review and approval semantics
- runtime-context metadata generation
- unsupported-path rejection for hosted tools, MCP, and handoffs

Primary file:

- [`tests/test_openai_agents_integration.py`](../../tests/test_openai_agents_integration.py)

### 2. Local End-To-End Smoke Tests

Test:

- fake-model agent run that emits a function call
- one tool execution loop
- final assistant message

Rules:

- must stay offline
- must not require `OPENAI_API_KEY`

### 3. Packaged Eval Suite

Test:

- stable case counts
- expected action sequences
- expected event-kind sequences
- runtime-context correlation on nested side effects

Rules:

- evals must be deterministic
- evals must not depend on hosted OpenAI services

### 4. Full Regression

Always run:

- `python -m pytest tests/ -q`
- `python -m agentfirewall.evals.langgraph`
- `python -m agentfirewall.evals.generic`

Reason:

- the second-adapter candidate must not destabilize LangGraph or the generic preview path

## Recommended Implementation Order

Use this order unless there is a strong reason to change it:

1. Add OpenAI packaged eval suite.
2. Add OpenAI helper tools for shell, file, and HTTP.
3. Add OpenAI eval expectations and candidate release gate.
4. Update capability docs and runtime-support inventory.
5. Decide whether to promote OpenAI Agents into the official adapter registry.

## What To Avoid

- do not broaden the OpenAI scope to hosted tools just because the SDK exposes them
- do not mix AgentFirewall review semantics with SDK-native approval semantics
- do not add MCP support through the OpenAI adapter path
- do not mark OpenAI Agents as official before packaged evidence exists
- do not skip offline test coverage in favor of real API runs

## Success Criteria

This plan is successful when developers can honestly say all of the following:

- OpenAI Agents reuses the same runtime firewall core as LangGraph
- the adapter remains small and understandable
- the supported boundary is narrower than the SDK surface, but clearly documented
- local evidence proves prompt and function-tool behavior
- nested side effects still carry the same runtime-context contract
- promotion to official-adapter status is based on evidence, not ambition
