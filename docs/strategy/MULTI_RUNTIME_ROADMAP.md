# Multi-Runtime Roadmap

## Goal

Build one runtime firewall core that can protect tool-using AI systems across multiple adapters without changing policy semantics, approval behavior, or audit shape.

## Current Shipping Position

`1.0.0` ships one supported runtime path: LangGraph.

This is deliberate.

The first job is to prove that the core event model, enforcement surfaces, and audit traces are stable enough that a second adapter can reuse them without special-casing the product around LangGraph.

## Planning Rule

Standardize execution surfaces, not framework-specific APIs.

Every new adapter should translate runtime behavior into shared event kinds such as:

- `prompt`
- `tool_call`
- `command`
- `file_access`
- `http_request`

New event kinds should be added only when a genuinely new surface appears, not because a framework exposes a different API.

## Target Architecture

1. Core policy engine
   Normalized events, decisions, policy packs, approval flow, audit schema.
2. Execution-surface enforcers
   Shared enforcement at tool dispatch, shell, file, and outbound HTTP boundaries.
3. Adapter SPI
   A small contract for translating runtime-specific hooks into shared events and runtime-context metadata.
4. Official adapters
   LangGraph today, additional agent runtimes next, then MCP-oriented paths.
5. Compatibility kit
   Capability matrix, conformance tests, and example workflows that every official adapter must pass.

## Expansion Order

### 1. Adapter Contract Hardening

Near-term goal:

- define the adapter capability matrix
- document required runtime-context fields
- add conformance tests for prompt, tool, shell, file, HTTP, review, and `log-only`
- keep one shared audit schema across adapters

Why first:

- this proves the core is reusable
- this prevents adapter-specific semantics from leaking into policy code
- this makes future runtime work additive instead of destabilizing

### 2. Second Official Adapter

Near-term goal:

- add one more tool-calling runtime with strong overlap to the current LangGraph path
- prove the same policy pack and audit model can work across two adapters
- keep setup lightweight enough that the integration still feels "drop-in"

Success signal:

- a new user can see the same `allow` / `block` / `review` / `log` flow without learning a second policy model

### 3. MCP Client / Server Support

Near-term goal:

- support outbound MCP client calls through the same decision model
- support guarded MCP server-side execution surfaces where side effects can happen
- normalize MCP tool and resource access into the shared audit trail

Important constraint:

- MCP should reuse the same core semantics where possible
- MCP-specific event types should only be introduced for truly new surfaces

### 4. Generic Wrappers

Near-term goal:

- provide low-level wrappers for runtimes that do not yet have a first-class adapter
- keep `log-only` onboarding available before hard blocking
- let users adopt the shared enforcement surfaces without waiting for official runtime support

Examples:

- direct tool-dispatch wrapper
- guarded subprocess wrapper
- guarded filesystem wrapper
- guarded HTTP wrapper

### 5. Broader Deployment Patterns

Later goal:

- explore sidecar, proxy, or centrally managed deployment once the in-process SDK model is stable

This comes later because:

- the strongest current value is execution-path context
- premature deployment complexity would slow adapter quality
- centralized control without stable event semantics would create churn

## Prioritization Criteria For New Adapters

- strong overlap with tool-using workflows
- ability to enforce before side effects happen
- high reuse of the existing event model
- local reproducibility for demos and evals
- clear `log-only` adoption path before enforcement

## Near-Term Milestones

### 1.1

- finalize adapter SPI
- add adapter capability matrix
- add conformance tests and example traces

### 1.2

- ship a second official runtime adapter
- keep policy and audit behavior aligned with LangGraph

### 1.3

- ship MCP-oriented client/server support on the shared core
- document where MCP reuses existing event kinds and where it needs new ones

### 1.4

- ship generic wrappers for unsupported runtimes
- make `log-only` the default validation path for new integrations

## What Not To Do

- do not claim universal compatibility before adapter evidence exists
- do not fork policy logic by framework
- do not let runtime-specific marketing outrun the supported contract
- do not add centralized control planes before the adapter layer is stable
