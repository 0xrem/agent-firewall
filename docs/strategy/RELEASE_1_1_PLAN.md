# 1.1 Plan

## Release Theme

`1.1` should be an adapter-contract hardening release.

The goal is not to add broad new runtime coverage yet.

The goal is to make the current runtime firewall core reusable enough that the next adapter can plug in without changing policy semantics, approval behavior, or audit shape.

## Why `1.1` Exists

`1.0.0` proves one supported LangGraph path.

That is enough to claim a stable first adapter, but it is not yet enough to claim that AgentFirewall is truly multi-runtime by design.

`1.1` should close that gap by turning the current LangGraph path into a reusable adapter reference implementation.

## Product Goal

After `1.1`, the repo should be able to say:

- the runtime firewall core is adapter-oriented, not LangGraph-shaped
- official adapters are expected to implement a documented capability contract
- every official adapter is validated by the same conformance kit
- LangGraph still passes the same user-visible behavior after the refactor

## Non-Goals

Do not make these part of `1.1`:

- a second official runtime adapter
- MCP client or server support
- a reviewer UI or centralized approval workflow
- sidecar, proxy, or centralized deployment models
- major policy-pack expansion beyond what the current surfaces require
- broad false-positive tuning for unknown production workloads

## Release Deliverables

`1.1` should ship five concrete deliverables:

1. A documented adapter SPI.
2. A documented adapter capability matrix.
3. A documented runtime-context contract.
4. A reusable conformance test kit.
5. A LangGraph adapter refactor that passes the new contract without changing user-visible behavior.

## Architecture Scope

### 1. Core Remains Runtime-Agnostic

The following layers should remain free of runtime-specific assumptions:

- normalized event kinds
- decisions and approval semantics
- audit entry shape
- policy packs and rule execution
- execution-surface enforcers for shell, file, and HTTP

Success condition:

- a new adapter should only need to translate runtime hooks into shared events and runtime-context metadata

### 2. Adapter Layer Becomes Explicit

`1.1` should introduce a clear internal adapter boundary, even if the first implementation still only ships one official adapter.

That boundary should answer four questions:

1. how prompt inspection is connected
2. how tool dispatch is intercepted
3. how runtime context is propagated into nested side effects
4. how adapter capabilities are declared and tested

### 3. LangGraph Becomes The Reference Adapter

LangGraph should remain the only officially supported runtime path in `1.1`.

But after `1.1`, LangGraph should be the first example of the adapter contract, not the shape that every future integration must copy informally.

## Proposed `1.1` Internal Structure

The exact module names can change, but the responsibilities should look like this:

### Core

- `events`
  Owns normalized event kinds and payload semantics.
- `policy`
  Owns decision semantics and rule evaluation.
- `approval`
  Owns review resolution semantics.
- `audit`
  Owns audit entry and summary schema.
- `enforcers`
  Own shared shell, file, and HTTP guarded execution surfaces.
- `runtime_context`
  Owns correlation metadata propagation across nested events.

### Adapter Contract

- adapter metadata model
- capability declaration model
- runtime-context field contract
- shared conformance fixtures and assertions
- runtime translation helpers for prompt extraction, tool dispatch normalization, and tool-context propagation
- shared adapter assembly helpers for resolving a firewall from either an existing object or supported high-level factory options
- shared adapter surface builders for shell, file, and HTTP guarded tool setup

### Official Adapter

- LangGraph adapter hooks
- LangGraph guarded tools built via an internal surface-builder layer on shared enforcers
- LangGraph-specific examples, evals, and docs

## Adapter SPI Requirements

`1.1` should document an internal adapter SPI with the following minimum responsibilities.

### Required Responsibilities

- translate runtime prompts into `prompt` events when prompt inspection is supported
- translate runtime tool dispatch into `tool_call` events before execution
- propagate runtime metadata so nested `command`, `file_access`, and `http_request` events can be linked back to the originating tool call
- preserve `review` and `log-only` semantics exactly as the core defines them
- expose adapter capabilities in a machine-readable way

### Explicit Non-Requirements

- no requirement that every adapter support every execution surface on day one
- no requirement that every adapter expose identical setup APIs
- no requirement that every adapter implement its own approval system

### Stability Rule

`1.1` should treat the adapter SPI as internal-but-deliberate:

- stable enough to build a second adapter on top of it
- still allowed to evolve before it becomes a public extension API

## Capability Matrix

`1.1` should add a documented capability matrix for every official adapter.

The matrix should answer:

- does the adapter support prompt inspection
- does it support tool-call interception
- does it support shell enforcement
- does it support file read enforcement
- does it support file write enforcement
- does it support outbound HTTP enforcement
- does it preserve runtime-context correlation
- does it support `review`
- does it support `log-only`
- what is the current support level: experimental, supported, or reference-only

For `1.1`, LangGraph should be the first filled-in row of that matrix.

## Runtime-Context Contract

`1.1` should document which `runtime_context` fields are required for side-effect events produced inside an adapter-managed workflow.

Minimum required fields:

- `runtime`
- `tool_name`
- `tool_call_id`
- `tool_event_source`

Rules:

- these fields are required on nested side-effect events when a tool call triggered the action
- they are optional on top-level events with no parent tool context
- adapters may add extra fields, but must not change the meaning of the required ones

## Audit Schema Expectations

`1.1` should freeze the minimum audit shape expected from official adapters.

Every official adapter trace used in docs, evals, or conformance tests should include:

- `event.kind`
- `event.operation`
- `event.source`
- `decision.action`
- `decision.rule`
- `decision.metadata`

For workflow-oriented traces, the emitted summary should continue to include:

- `action_counts`
- `event_kind_counts`
- `rule_counts`
- `source_counts`
- `tool_name_counts`

## Work Packages

### 1. Adapter Contract Package

Ship:

- adapter capability model
- adapter status vocabulary
- runtime-context contract doc
- adapter conformance checklist

Definition of done:

- the repo has one place that defines what an official adapter must guarantee

### 2. LangGraph Refactor Package

Ship:

- LangGraph adapter aligned to the adapter contract
- a shared internal surface-builder path for LangGraph shell, file, and HTTP tools
- no change to current supported setup path
- no change to current user-visible semantics for prompt, tool, shell, file, HTTP, review, or `log-only`

Definition of done:

- current LangGraph docs and examples remain valid after the refactor

### 3. Conformance Kit Package

Ship:

- reusable test helpers or fixtures for adapter conformance
- required trace assertions
- capability-driven test expectations
- registry-backed eval evidence entrypoints for official adapters
- a shared release-gate entrypoint that combines conformance and eval expectations

Definition of done:

- LangGraph passes the same contract tests that a future second adapter will need to pass

### 4. Documentation Package

Ship:

- `1.1` release plan
- adapter capability matrix
- documented relationship between supported path and future adapters

Definition of done:

- a contributor can understand how to add the next adapter without reverse-engineering LangGraph internals

Reference docs:

- [`ADAPTER_CAPABILITY_MATRIX.md`](./ADAPTER_CAPABILITY_MATRIX.md)
- [`MULTI_RUNTIME_ROADMAP.md`](./MULTI_RUNTIME_ROADMAP.md)

## Acceptance Metrics

`1.1` is done when all of the following are true:

### Product Metrics

- the repo has one documented adapter contract that future adapters can target
- LangGraph remains the only official adapter, but no longer acts as an undocumented special case
- the supported `1.0.0` path remains intact from a user point of view

### Engineering Metrics

- the LangGraph adapter passes the full current eval suite without semantic regression
- the LangGraph adapter passes the new adapter conformance suite
- all required runtime-context fields appear in every relevant side-effect trace
- audit summaries stay JSON-friendly and stable for local tooling

### Documentation Metrics

- the capability matrix exists in-repo
- the required runtime-context fields are documented in one place
- the `1.1` non-goals are explicit enough to prevent scope creep into MCP or a second adapter

## Regression Guardrails

`1.1` must not regress the current supported LangGraph behavior.

At minimum, these user-visible behaviors must stay the same:

- prompt review before model execution
- tool-call review for sensitive tools
- guarded shell command blocking
- guarded file read and write blocking
- guarded outbound HTTP host blocking
- `log-only` traces preserving `decision_metadata.original_action`
- side-effect traces linking back to the originating tool call

## Test Plan

### 1. Unit Tests

Add or tighten unit tests for:

- adapter capability declarations
- runtime-context required field validation
- audit schema serialization
- capability-driven expectation resolution

### 2. Contract Tests

Create an adapter conformance suite that checks:

- prompt support when declared
- tool-call interception when declared
- side-effect correlation when shell, file, or HTTP support is declared
- `review` semantics stay unchanged
- `log-only` semantics stay unchanged
- audit summaries expose the required aggregate counters

These tests should be capability-aware so a future adapter can skip unsupported surfaces explicitly instead of silently failing.

### 3. Integration Tests

Keep the LangGraph integration tests as the runtime-specific proof path for:

- safe tool workflows
- reviewed tool workflows
- approved and denied review outcomes
- command, file, and HTTP enforcement
- multi-step workflow traces

### 4. Eval Regression Tests

The packaged LangGraph eval suite should remain a release gate.

Release target:

- `19 / 19` passing
- same status distribution unless an intentional fixture change is documented
- no unexpected allows, unexpected blocks, or unexpected reviews

### 5. Example And Doc Verification

Before closing `1.1`, re-run:

- `python examples/attack_scenarios.py`
- `python examples/langgraph_quickstart.py`
- `python examples/langgraph_agent.py`
- `python examples/langgraph_trial_run.py`
- `python -m agentfirewall.evals.langgraph`
- `python -m pytest tests/ -v`

## Suggested Implementation Order

1. write the adapter contract and capability vocabulary
2. define the runtime-context field contract
3. extract shared conformance assertions from the current LangGraph tests and evals
4. align the LangGraph adapter to the contract without changing behavior
5. document the LangGraph capability row and release evidence

## Exit Criteria Before `1.2`

Do not start the second official adapter until all of these are true:

1. the adapter contract is documented and used by LangGraph
2. LangGraph passes both integration tests and adapter conformance tests
3. the required runtime-context fields are stable in traces
4. the supported-path docs still match the real LangGraph setup flow
5. the team can explain what a future adapter must implement in one document set

## Why This Belongs In GitHub

This document is suitable for the public repo because it does not expose private roadmap timing or sensitive commercial information.

It does document:

- architectural intent
- scope boundaries
- release-quality expectations
- what contributors should and should not build next

That makes it useful both for internal alignment and for external contributors who want to understand the next release direction.
