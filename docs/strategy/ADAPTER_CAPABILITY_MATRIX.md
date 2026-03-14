# Adapter Capability Matrix

## Purpose

This document defines the capability vocabulary that official adapters are expected to declare and that conformance tests are expected to validate.

It is intentionally narrower than a full product-comparison matrix.

Its job is to answer one question clearly:

What does an adapter actually guarantee today?

The source of truth for official adapter rows and registry-backed eval evidence lives in code through `RuntimeAdapterSpec`, `export_official_adapter_matrix()`, and `export_official_adapter_inventory()`.

## Official Support-Level Vocabulary

- `supported`
  Part of the current official supported path.
- `experimental`
  Implemented, but not yet part of the stable supported path.
- `reference_only`
  Intended as a reference implementation or internal proving path, not a support promise.

## Capability Cell Vocabulary

- `supported`
  The adapter declares this capability today.
- `not_supported`
  The adapter does not declare this capability today.
- `planned`
  Roadmap direction only for a non-official future path.

## Capability Definitions

- `prompt_inspection`
  The adapter can route prompt inspection through the shared `prompt` event path before the relevant runtime step continues.
- `tool_call_interception`
  The adapter can evaluate tool dispatch through the shared `tool_call` event path before execution.
- `shell_enforcement`
  The adapter exposes an official path that routes shell execution through shared guarded subprocess enforcement.
- `file_read_enforcement`
  The adapter exposes an official path that routes file reads through shared guarded filesystem enforcement.
- `file_write_enforcement`
  The adapter exposes an official path that routes file writes through shared guarded filesystem enforcement.
- `http_enforcement`
  The adapter exposes an official path that routes outbound HTTP through shared guarded network enforcement.
- `runtime_context_correlation`
  Nested side-effect events include the required `runtime_context` fields when they originate from a tool call.
- `review_semantics`
  The adapter preserves core `review` behavior without redefining approval semantics.
- `log_only_semantics`
  The adapter preserves core `log-only` behavior without redefining decision semantics.

## Current Official Matrix

| Adapter | Status | Prompt | Tool Call | Shell | File Read | File Write | HTTP | Runtime Context | Review | Log Only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `agentfirewall.langgraph` | `supported` | `supported` | `supported` | `supported` | `supported` | `supported` | `supported` | `supported` | `supported` | `supported` |
| `agentfirewall.openai_agents` | `supported` | `supported` | `supported` | `supported` | `supported` | `supported` | `supported` | `supported` | `supported` | `supported` |

## Current `1.2.0` Interpretation

For `1.2.0`, both `agentfirewall.langgraph` and `agentfirewall.openai_agents` are part of the official supported adapter contract.

Preview runtime support for `generic_wrappers` is exported separately through `agentfirewall.runtime_support`, but that row is not part of the official adapter matrix.

## Planning Direction Only

These rows are roadmap guidance, not an adapter contract:

| Future Path | Status | Prompt | Tool Call | Shell | File Read | File Write | HTTP | Runtime Context | Review | Log Only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MCP client path | `planned` | `planned` | `planned` | `not_supported` | `planned` | `planned` | `planned` | `planned` | `planned` | `planned` |
| MCP server path | `planned` | `planned` | `planned` | `planned` | `planned` | `planned` | `planned` | `planned` | `planned` | `planned` |

## `1.1` Expectation

`1.1` should make this matrix part of the adapter contract.

That means:

- every official adapter must publish a row
- the conformance suite must map tests to these capabilities
- docs should avoid claiming support for a capability that the matrix does not mark as `supported`
