# 1.3 Plan

## Release Theme

`1.3` should be the MCP preview and resource-surface release.

The goal is not to claim full MCP compatibility.

The goal is to extend the shared runtime firewall core into MCP-oriented client and server flows without changing policy semantics, review behavior, audit shape, or nested side-effect correlation.

## Why `1.3` Exists

`1.2.0` already proved the core can span two official adapters:

- LangGraph
- OpenAI Agents SDK

That means the next real product question is no longer "can we support a second runtime?"

The next real question is:

- can the same core model survive a protocol-shaped integration
- can AgentFirewall protect tool calls and data reads that do not look like framework-local tools
- can we widen coverage without overpromising official support too early

MCP is the right next step because it introduces one genuinely new execution surface:

- resource access

Tool invocation can still reuse the shared `tool_call` model.

Resource access should not be faked as `file_access` or `http_request`.

## Product Goal

After `1.3`, the repo should be able to say:

- the two existing official adapters remain stable and release-gated
- AgentFirewall has documented MCP-oriented preview support for both client-side and server-side flows
- MCP tool calls reuse the same `allow` / `block` / `review` / `log-only` semantics as other runtimes
- MCP resource reads are represented as a first-class shared surface instead of runtime-specific special cases
- nested shell, file, and HTTP side effects can still be correlated back to the originating MCP tool flow

## Non-Goals

Do not make these part of `1.3`:

- universal or official MCP compatibility claims
- every MCP SDK or transport
- sampling
- prompts
- roots
- subscriptions
- notifications
- browser-based transports
- remote auth, hosted control planes, or centralized reviewer services
- a third official adapter promotion
- policy-pack sprawl for hypothetical MCP-only edge cases before evidence exists

## Release Deliverables

`1.3` should ship six concrete deliverables:

1. A shared `resource_access` event surface in the core model.
2. A preview `agentfirewall.mcp` API for MCP-oriented client and server integration.
3. Deterministic local MCP loopback fixtures for tests, demos, and evals.
4. Packaged local eval suites for MCP client and MCP server preview paths.
5. Runtime-support inventory rows and support docs that describe the preview boundary honestly.
6. A promotion checkpoint that decides whether MCP remains preview after `1.3` or is ready for later officialization.

## Status Rule

`1.3` should treat MCP as preview support, not as an official adapter contract.

That means:

- MCP should appear in preview runtime inventory
- MCP should ship with local evidence and clear docs
- MCP should not be added to the official adapter registry in `1.3`

Promotion can happen in a later release after the preview boundary proves stable.

## Architecture Scope

### 1. Reuse Existing Event Kinds Where They Fit

For `1.3`, MCP should reuse existing event kinds whenever the semantics already match:

- MCP tool invocation -> `tool_call`
- nested shell execution -> `command`
- nested file read/write -> `file_access`
- nested outbound HTTP -> `http_request`

Do not invent MCP-specific event kinds for these.

### 2. Add One New Shared Surface: `resource_access`

MCP introduces a real new surface: reading a resource identified by a URI or server-defined handle.

That should become a new shared event kind:

- `resource_access`

Why:

- a resource is not always a file
- a resource is not always an outbound HTTP request
- pretending otherwise would make policy behavior confusing and audit traces misleading

Initial `1.3` scope for `resource_access`:

- operation: `read`
- payload fields:
  - `uri`
  - `scheme`
  - `server_name` when known
  - `mime_type` when known

Out of scope for `1.3`:

- subscriptions
- push updates
- streaming resource deltas
- advanced resource mutation semantics

### 3. Keep The Core Runtime-Agnostic

The following layers must remain runtime-agnostic even after MCP support lands:

- `events`
- `policy`
- `approval`
- `audit`
- shared enforcers for shell, file, and HTTP
- eval contracts
- support inventory export

MCP-specific code belongs in adapter or preview-integration layers, not in policy logic.

### 4. Keep Required Runtime Context Stable

The required runtime-context contract should stay unchanged:

- `runtime`
- `tool_name`
- `tool_call_id`
- `tool_event_source`

`1.3` may add optional MCP metadata such as:

- `protocol="mcp"`
- `mcp_direction`
- `mcp_server_name`
- `mcp_resource_uri`
- `mcp_operation`

These are optional enrichments, not new required fields for all adapters.

## Proposed `1.3` Module Shape

The exact filenames can still move, but the responsibilities should converge on this shape:

### Core Changes

- `src/agentfirewall/events.py`
  - add `resource_access`
  - add a constructor such as `EventContext.resource_access(...)`
- `src/agentfirewall/integrations/contracts.py`
  - add a capability for resource interception
- `src/agentfirewall/runtime_context.py`
  - add helper support for optional MCP metadata without changing required fields
- `src/agentfirewall/runtime_support.py`
  - export preview MCP client and MCP server rows with packaged evidence

### MCP Preview Integration

- `src/agentfirewall/integrations/mcp.py`
  - MCP client translator helpers
  - MCP server translator helpers
  - shared MCP metadata normalization
- `src/agentfirewall/mcp.py`
  - public preview entrypoints
  - client bundle factory
  - server bundle factory
  - guarded tool/resource wrapper helpers

### Evidence And Validation

- `src/agentfirewall/evals/mcp_client.py`
- `src/agentfirewall/evals/mcp_server.py`
- `src/agentfirewall/evals/cases/mcp_client_cases.json`
- `src/agentfirewall/evals/cases/mcp_server_cases.json`
- `tests/test_mcp_client_integration.py`
- `tests/test_mcp_server_integration.py`
- `tests/test_mcp_evals.py`

### Examples

- `examples/mcp_client_demo.py`
- `examples/mcp_server_demo.py`

## Public Preview API Requirements

`1.3` should expose a narrow, transport-agnostic preview API.

Recommended public surface:

- `create_client_bundle(...)`
- `create_server_bundle(...)`
- `create_tool_wrapper(...)`
- `create_resource_reader(...)`

Design rule:

- wrap callables or session-like interfaces
- do not make the first public API depend on one concrete network transport
- do not make the first public API depend on hosted services

The preview API should feel like the current generic and OpenAI bundles:

- one firewall
- one grouped setup path
- deterministic local behavior

## Workstreams

### Workstream 1: Shared Surface Contract

Ship:

- `resource_access` event kind
- event payload normalization
- capability vocabulary update
- audit serialization update if needed

Definition of done:

- core code can represent `resource_access` without special-casing MCP everywhere
- policy evaluation and audit export work for the new event kind
- no existing adapter behavior changes unintentionally

### Workstream 2: MCP Client Preview Path

Ship:

- tool-call interception for outbound MCP tool calls
- resource-read interception for outbound MCP resource reads
- `review` / `block` / `log-only` semantics on both surfaces
- deterministic local client fixture

Definition of done:

- a client-side wrapper can guard a tool invocation before it leaves the local process
- a client-side wrapper can guard a resource read before it happens
- traces clearly show MCP metadata when available

### Workstream 3: MCP Server Preview Path

Ship:

- wrapper helpers for local MCP tool handlers
- wrapper helpers for local MCP resource readers
- nested runtime-context propagation into shell/file/http enforcers when local handlers trigger side effects

Definition of done:

- local MCP server handlers can reuse the same guarded execution surfaces as other runtimes
- blocked or reviewed side effects still correlate back to the originating MCP tool flow

### Workstream 4: Evidence Package

Ship:

- packaged local eval suites
- fake or loopback MCP fixtures
- offline demo examples
- preview runtime inventory entries

Definition of done:

- contributors can validate the preview path without network access
- evidence is strong enough to discuss the support boundary honestly

### Workstream 5: Docs And Promotion Checkpoint

Ship:

- updated roadmap, product-status, and supported-path docs
- explicit "supported" versus "not supported" MCP boundary
- a go/no-go note on whether MCP remains preview after `1.3`

Definition of done:

- a collaborator can tell exactly what to build and what not to touch
- a user can tell exactly what MCP support means in `1.3`

## Recommended Execution Order

Use this order to avoid drift:

1. Add the shared `resource_access` surface.
2. Add deterministic fake or loopback MCP fixtures.
3. Build the MCP client preview wrappers.
4. Build the MCP server preview wrappers.
5. Add packaged evals and preview runtime inventory rows.
6. Update docs and make the promotion decision.

Do not invert this order by starting with broad SDK integrations or transport support first.

## Concrete Requirements

### Required Behavior

`1.3` must preserve all of the following:

- LangGraph official adapter remains release-gated
- OpenAI Agents official adapter remains release-gated
- generic wrappers remain the documented preview fallback
- MCP preview uses the same decision vocabulary:
  - `allow`
  - `block`
  - `review`
  - `log`

### Required Evidence

`1.3` must include all of the following before it is considered complete:

- local MCP client eval suite
- local MCP server eval suite
- preview runtime inventory rows for MCP client and MCP server
- offline example scripts
- integration tests covering nested side-effect correlation

### Required Boundary Discipline

MCP work must not:

- fork policy rules by protocol
- bypass shared enforcers
- hide blocked or reviewed actions as normal tool outputs
- pull in hosted transports just to make the demo look broader
- upgrade MCP to official support without a later explicit decision

## Testing Plan

### Unit Tests

Add unit coverage for:

- `resource_access` payload normalization
- URI parsing and server-name normalization
- MCP metadata propagation helpers

### Integration Tests

Minimum MCP client integration coverage:

- safe tool call
- blocked tool call
- review-required tool call
- approved reviewed tool call
- safe resource read
- blocked resource read
- `log-only` client flow

Minimum MCP server integration coverage:

- safe local tool handler
- blocked local tool handler
- safe local resource reader
- blocked local resource reader
- nested shell/file/http side-effect correlation
- `log-only` server flow

### Eval Suites

Minimum packaged evidence target for `1.3`:

- MCP client preview: at least 6 local cases
- MCP server preview: at least 6 local cases

The eval suites must:

- run offline
- avoid external MCP services
- avoid non-deterministic network behavior
- emit traces with clear action and event counts

### Regression Validation

Every MCP PR should still run:

- `python -m pytest tests/ -q`
- `python -m agentfirewall.evals.langgraph`
- `python -m agentfirewall.evals.openai_agents`
- `python -m agentfirewall.evals.generic`

When MCP evals land, also run:

- `python -m agentfirewall.evals.mcp_client`
- `python -m agentfirewall.evals.mcp_server`

## Collaboration Rules

This section is for collaborators working on `1.3`.

### Good Tasks To Parallelize

- core `resource_access` surface work
- MCP client wrappers
- MCP server wrappers
- eval fixtures and case files
- examples and support-inventory updates

### Tasks That Should Not Drift

- do not add GitHub Pages or site work to `main`
- do not add translation scripts or summary scripts
- do not add broad docs claims before code and evidence exist
- do not add policy rules that only exist for one transport experiment

### PR Quality Bar

Every MCP PR should include:

- code
- tests
- at least one local validation path
- support-boundary documentation if the surface changes

No implementation-only PR should change the public support promise silently.

## Exit Criteria Before A Later MCP Promotion

MCP should stay preview after `1.3` unless all of the following become true:

- client and server preview paths stay stable across several iterations
- local eval evidence remains green and meaningful
- the support boundary can be explained in one short paragraph
- users can adopt the path in `log-only` without framework-specific guesswork
- the product still does not need protocol-specific policy forks

If any of those are still weak, keep MCP preview and keep the promise narrow.

## Summary

The correct next move after `1.2.0` is not "support all of MCP."

The correct next move is:

- add one honest new shared surface
- prove MCP client and server preview paths on the shared core
- keep the promise narrow
- keep the evidence local and repeatable

That is the fastest path that still protects the main product goal.
