# 1.3 Issue Backlog

## Purpose

This document turns the `1.3` plan into concrete issue-sized work items.

It is intended for collaborators who need actionable scopes, acceptance criteria, dependencies, and validation commands instead of high-level roadmap language.

Use this together with:

- [`RELEASE_1_3_PLAN.md`](./RELEASE_1_3_PLAN.md)
- [`APPLICATION_ADOPTION.md`](./APPLICATION_ADOPTION.md)
- [`PRODUCT_STATUS.md`](./PRODUCT_STATUS.md)

## How To Use This Backlog

- Start with Track A before Track B.
- Within each track, respect the dependency order.
- Do not widen scope inside one issue just because related code is nearby.
- Every issue should preserve the current `1.2.0` support contract for LangGraph and OpenAI Agents.

Priority legend:

- `P0`: blocks the milestone
- `P1`: important but can start after the first P0 lands
- `P2`: valuable parallel work that should not distort the main path

## Track A: 1.3 Core And MCP Preview

This is the main line of development.

### AF-1301 `P0` Add `resource_access` to the core event model

Goal:

- introduce a first-class shared surface for MCP-style resource reads

In scope:

- add `RESOURCE_ACCESS` to `EventKind`
- add `EventContext.resource_access(...)`
- normalize `uri`, `scheme`, `server_name`, and `mime_type`
- ensure serialization works with the new event kind

Out of scope:

- resource writes
- subscriptions
- streaming updates
- MCP transport code

Likely files:

- `src/agentfirewall/events.py`
- `src/agentfirewall/serialization.py`
- `tests/` unit coverage for event normalization

Acceptance criteria:

- a `resource_access` event can be created, serialized, and audited
- no existing event kind changes behavior
- the new surface does not require protocol-specific branching in policy code

Validation:

- `python -m pytest tests/ -q`

Dependencies:

- none

### AF-1302 `P0` Extend capability and support-contract vocabulary for resource interception

Goal:

- make the new shared surface visible in adapter and preview support contracts

In scope:

- add a resource-interception capability to the adapter contract vocabulary
- update capability ordering and matrix export
- prepare preview runtime rows for future MCP client/server entries

Out of scope:

- declaring MCP official support
- modifying official adapter support levels

Likely files:

- `src/agentfirewall/integrations/contracts.py`
- `src/agentfirewall/runtime_support.py`
- `docs/strategy/ADAPTER_CAPABILITY_MATRIX.md`
- tests for capability export

Acceptance criteria:

- contracts can represent `resource_access` support cleanly
- existing official adapter exports remain stable
- runtime-support export still works after the new capability lands

Validation:

- `python -m pytest tests/ -q`
- `python -m agentfirewall.runtime_support --include-evidence`

Dependencies:

- AF-1301

### AF-1303 `P0` Add MCP metadata helpers without changing required runtime-context fields

Goal:

- support MCP-specific correlation metadata while preserving the shared contract

In scope:

- add helpers for optional fields such as `mcp_direction`, `mcp_server_name`, `mcp_resource_uri`, and `mcp_operation`
- keep required fields unchanged:
  - `runtime`
  - `tool_name`
  - `tool_call_id`
  - `tool_event_source`

Out of scope:

- making MCP metadata required for all adapters
- changing the meaning of existing runtime-context fields

Likely files:

- `src/agentfirewall/runtime_context.py`
- tests for context building and attachment

Acceptance criteria:

- MCP preview paths can enrich context without breaking current adapters
- LangGraph and OpenAI tests keep passing unchanged

Validation:

- `python -m pytest tests/ -q`

Dependencies:

- none

### AF-1304 `P0` Build deterministic local MCP loopback fixtures

Goal:

- create an offline, transport-light way to test MCP-style client/server flows

In scope:

- fake or loopback client fixture for tool calls and resource reads
- fake or loopback server fixture for local handlers
- deterministic behavior suitable for tests, evals, and examples

Out of scope:

- real hosted MCP services
- browser transports
- auth flows

Likely files:

- `tests/fixtures/` or `src/agentfirewall/evals/` helper code
- future `examples/mcp_*` support files

Acceptance criteria:

- fixtures run offline
- fixtures support safe, blocked, and review-required paths
- fixtures expose enough metadata to test audit traces

Validation:

- fixture-specific pytest coverage

Dependencies:

- AF-1301
- AF-1303

### AF-1305 `P0` Implement MCP client preview wrappers

Goal:

- guard outbound MCP-style tool calls and resource reads before they happen

In scope:

- preview client bundle
- tool-call wrapper
- resource-read wrapper
- `review`, `block`, and `log-only` semantics on both surfaces

Out of scope:

- official adapter promotion
- sampling
- prompts
- subscriptions

Likely files:

- `src/agentfirewall/integrations/mcp.py`
- `src/agentfirewall/mcp.py`

Acceptance criteria:

- client wrappers emit `tool_call` for tool invocations
- client wrappers emit `resource_access` for resource reads
- traces include MCP metadata when available
- behavior stays aligned with core decision semantics

Validation:

- `python -m pytest tests/test_mcp_client_integration.py -q`

Dependencies:

- AF-1301
- AF-1303
- AF-1304

### AF-1306 `P1` Add MCP client integration tests

Goal:

- lock down the client preview behavior with regression coverage

Required cases:

- safe tool call
- blocked tool call
- review-required tool call
- approved reviewed tool call
- safe resource read
- blocked resource read
- `log-only` client flow

Acceptance criteria:

- the test file explains the actual support boundary
- test names map cleanly to later eval cases
- failures are understandable enough for contributors to debug

Validation:

- `python -m pytest tests/test_mcp_client_integration.py -q`

Dependencies:

- AF-1305

### AF-1307 `P1` Add MCP client packaged eval suite

Goal:

- produce repeatable local evidence for the client preview path

In scope:

- `src/agentfirewall/evals/mcp_client.py`
- `src/agentfirewall/evals/cases/mcp_client_cases.json`
- CLI entrypoint via module execution

Minimum target:

- at least 6 local cases

Acceptance criteria:

- eval suite runs offline
- expected statuses are explicit
- summary is compatible with support-inventory export

Validation:

- `python -m agentfirewall.evals.mcp_client`

Dependencies:

- AF-1305
- AF-1306

### AF-1308 `P0` Implement MCP server preview wrappers

Goal:

- guard local MCP-style tool handlers and resource readers on the server side

In scope:

- preview server bundle
- tool handler wrappers
- resource reader wrappers
- nested side-effect correlation into shell/file/http enforcers

Out of scope:

- transport hosting
- network servers
- auth

Likely files:

- `src/agentfirewall/integrations/mcp.py`
- `src/agentfirewall/mcp.py`

Acceptance criteria:

- local handlers can be wrapped without changing core firewall semantics
- nested shell/file/http side effects inherit runtime context correctly
- reviewed or blocked nested side effects remain explainable

Validation:

- `python -m pytest tests/test_mcp_server_integration.py -q`

Dependencies:

- AF-1301
- AF-1303
- AF-1304

### AF-1309 `P1` Add MCP server integration tests

Goal:

- regression-cover server-side preview behavior

Required cases:

- safe local tool handler
- blocked local tool handler
- safe local resource reader
- blocked local resource reader
- nested shell/file/http side-effect correlation
- `log-only` server flow

Acceptance criteria:

- server behavior is testable without real transports
- tests prove correlation on nested side effects

Validation:

- `python -m pytest tests/test_mcp_server_integration.py -q`

Dependencies:

- AF-1308

### AF-1310 `P1` Add MCP server packaged eval suite

Goal:

- package local evidence for the server preview path

In scope:

- `src/agentfirewall/evals/mcp_server.py`
- `src/agentfirewall/evals/cases/mcp_server_cases.json`

Minimum target:

- at least 6 local cases

Acceptance criteria:

- eval suite runs offline
- cases map cleanly to the actual preview support boundary
- result summary is reusable in runtime support export

Validation:

- `python -m agentfirewall.evals.mcp_server`

Dependencies:

- AF-1308
- AF-1309

### AF-1311 `P1` Export MCP preview support through runtime support inventory

Goal:

- make MCP preview rows visible to docs, dashboards, and future release checks

In scope:

- add `mcp_client` preview row
- add `mcp_server` preview row
- wire packaged evidence into export
- keep official adapter inventory unchanged

Acceptance criteria:

- runtime support export shows MCP as preview, not official
- support notes describe the honest boundary

Validation:

- `python -m agentfirewall.runtime_support --include-evidence`
- `python -m pytest tests/ -q`

Dependencies:

- AF-1307
- AF-1310

### AF-1312 `P1` Add MCP preview examples and docs

Goal:

- give contributors and users a believable local preview path

In scope:

- `examples/mcp_client_demo.py`
- `examples/mcp_server_demo.py`
- docs updates in supported path, roadmap, and README if needed

Acceptance criteria:

- examples run offline
- examples demonstrate at least one safe flow and one blocked or reviewed flow
- docs do not claim official MCP support

Validation:

- run both examples locally
- `python -m pytest tests/ -q`

Dependencies:

- AF-1307
- AF-1310
- AF-1311

### AF-1313 `P1` Write the `1.3` preview promotion checkpoint

Goal:

- force an explicit decision on whether MCP stays preview after `1.3`

In scope:

- add or update docs summarizing what worked
- list what still blocks officialization
- confirm whether `resource_access` stayed generic and reusable

Acceptance criteria:

- a maintainer can answer "why is MCP still preview?" or "why is it ready to promote?" in one short paragraph

Validation:

- doc review only

Dependencies:

- AF-1311
- AF-1312

## Track B: Application Adoption And Trust

This track should support the core roadmap, not replace it.

Good rule:

- only take these issues in parallel if they strengthen official adapters, generic onboarding, or the `1.3` preview path

### AF-1314 `P2` Add service-style examples for real backend workflows

Goal:

- make the product feel more "application-ready" without widening the support contract

Example ideas:

- queue worker with guarded shell/file steps
- scheduled ops job with `log-only` first run
- internal document-processing task with reviewed file writes

Acceptance criteria:

- examples stay within the supported adapter or generic preview boundary
- examples teach rollout, not just mechanics

Validation:

- example-specific local runs

Dependencies:

- none

### AF-1315 `P2` Add more benign workflow evals on official adapters

Goal:

- improve product trust by showing what should succeed, not only what should block

In scope:

- add realistic benign workflows to LangGraph and OpenAI eval suites
- document why these should remain allowed

Acceptance criteria:

- benign workflows increase confidence without weakening the blocking story
- eval expectations remain explicit and deterministic

Validation:

- `python -m agentfirewall.evals.langgraph`
- `python -m agentfirewall.evals.openai_agents`

Dependencies:

- none

### AF-1316 `P2` Improve generic-wrapper onboarding for unsupported runtimes

Goal:

- reduce adoption friction outside the official adapters

In scope:

- clearer quickstart flow
- stronger bundle examples
- more explicit `log-only` rollout guidance

Acceptance criteria:

- a developer not using LangGraph or OpenAI can see a believable first adoption path in under one reading session

Validation:

- `python examples/generic_tool_dispatcher.py`
- `python -m agentfirewall.evals.generic`

Dependencies:

- none

### AF-1317 `P2` Add rollout guidance for `log-only` -> `review` -> `block`

Goal:

- give application developers a clearer safety rollout playbook

In scope:

- docs only
- examples from official adapters and generic preview path

Acceptance criteria:

- guidance is concrete enough that a team can follow it in a pilot
- language stays aligned with current support boundaries

Validation:

- doc review

Dependencies:

- none

## Suggested Milestone Slices

If contributors need smaller waves instead of one large backlog, use these slices.

### Slice 1: Core surface

- AF-1301
- AF-1302
- AF-1303

### Slice 2: MCP client preview

- AF-1304
- AF-1305
- AF-1306
- AF-1307

### Slice 3: MCP server preview

- AF-1308
- AF-1309
- AF-1310

### Slice 4: Export, docs, and promotion checkpoint

- AF-1311
- AF-1312
- AF-1313

### Slice 5: Adoption and trust support

- AF-1314
- AF-1315
- AF-1316
- AF-1317

## Definition Of "No Drift"

The backlog is being executed correctly if:

- the first merged issues strengthen the shared core
- MCP remains preview through `1.3`
- official adapter quality does not regress
- application-facing work improves adoption without inventing new unsupported promises

The backlog is drifting if:

- contributors start with flashy demos instead of the shared surface
- transport or hosted integration work starts before loopback fixtures exist
- docs promise official MCP support before the evidence exists
- application examples expand into browser automation or unrelated agent surfaces

## Validation Floor For Every PR

Every PR in this backlog should still keep the repo green with the smallest relevant command set.

Minimum:

- `python -m pytest tests/ -q`

Use these when relevant:

- `python -m agentfirewall.evals.langgraph`
- `python -m agentfirewall.evals.openai_agents`
- `python -m agentfirewall.evals.generic`
- `python -m agentfirewall.evals.mcp_client`
- `python -m agentfirewall.evals.mcp_server`
- `python -m agentfirewall.runtime_support --include-evidence`

## Maintainer Note

If you decide to turn these into GitHub issues, keep the titles and IDs stable enough that collaborators can map repo docs back to the tracker without translation.
