# AgentFirewall Product Direction

## One-Sentence Definition

AgentFirewall is an inline runtime firewall for AI agents. It evaluates high-risk actions before side effects happen and returns a policy decision such as `allow`, `block`, `review`, or `log`.

This document expands on the product position defined in `README.md`.

`README.md` is the canonical statement of product scope and positioning.

This file records phased architecture decisions, integration priorities, and sequencing for the current stage of the project.

## Product Boundary

AgentFirewall is not meant to be a generic static scanner, passive probe, or trust registry.

Its core job is runtime enforcement at the moment an agent is about to do something sensitive, such as:

- dispatch a tool
- execute a shell command
- read or write a sensitive file
- call an outbound network endpoint
- follow an instruction that overrides prior policy

## What Poisoned Skills Mean In Scope

Poisoned skills matter to AgentFirewall when they produce dangerous runtime behavior.

In scope:

- a poisoned skill that overrides instructions
- a poisoned skill that tries to read secrets
- a poisoned skill that attempts exfiltration
- a poisoned skill that triggers dangerous command execution
- a poisoned skill that routes requests to untrusted endpoints

Out of scope by default:

- proving a third-party skill is clean before load
- repository trust scoring
- signature verification pipelines
- full malware-style package scanning

Those controls are adjacent and may complement AgentFirewall, but they are not the core product.

## Desired End State

The long-term product should have five layers:

1. A core policy engine that evaluates normalized runtime events.
2. Enforcement hooks at prompt, tool, command, file, and network boundaries.
3. Framework adapters for supported Python agent runtimes.
4. Audit logging for blocked, reviewed, and high-risk actions.
5. Reusable policy packs for default, strict, and custom deployment modes.

## Preferred Integration Model

The primary mental model should be an explicit firewall instance:

```python
from agentfirewall import AgentFirewall

firewall = AgentFirewall()
agent = firewall.wrap_agent(agent)
```

This is preferable to making `protect(agent)` the main story because it keeps the runtime firewall visible as a first-class object.

`protect(agent)` can remain as a convenience helper, but it should not define the product architecture.

## Advanced Integration Model

Custom runtimes should also be able to integrate AgentFirewall directly at execution surfaces, for example:

- tool dispatch wrappers
- subprocess wrappers
- filesystem access layers
- HTTP client wrappers

This makes the product usable even when a framework-level `wrap_agent(...)` adapter does not exist yet.

## Product Route

### Phase 1: In-Process Python SDK

Build the core policy engine and normalized event model inside a Python package.

Why this comes first:

- easiest place to get full runtime context
- easiest place to block before side effects
- best fit for the current repo and team scope

### Phase 2: Framework Adapters

Add adapters for selected Python agent runtimes such as LangGraph, OpenAI Agents, and MCP-oriented Python runtimes.

Goal:

- make the default integration path close to one line
- keep custom runtimes supported through lower-level hooks

### Phase 3: Broader Deployment Patterns

Explore sidecar, proxy, or centrally managed deployment patterns after the SDK model is stable and the event model is proven.

This should come later, not first.

## 0.0.1 Milestone

The recommended first milestone is `0.0.1` as an internal preview, not a broad public maturity claim.

The goal is not to ship a large architecture skeleton. The goal is to ship one narrow but real end-to-end path that can evaluate and block runtime behavior.

Definition of done for `0.0.1`:

1. Stable event, decision, policy, and audit types.
2. A small built-in rule set for obvious runtime risks.
3. At least two real enforcement surfaces.
4. A runnable demo that shows allowed and blocked behavior.
5. Repeatable tests for attack cases and expected decisions.

## Current Assessment After 0.0.1

`0.0.1` proves the product direction, but it is still shallow in three important ways:

1. It has low-level execution helpers, but not yet a strong adapter boundary for real agent runtimes.
2. It has built-in rules, but not yet a robust configuration and policy-pack model.
3. It has local audit recording, but not yet the observability and regression infrastructure needed for steady iteration.

This means the next version should not chase breadth. It should make the current path operationally stronger.

## 0.0.2 Milestone

The recommended next milestone is `0.0.2` as an operational hardening release.

The purpose of `0.0.2` is to make the first runtime path more reliable, configurable, and testable without changing the product definition.

Definition of done for `0.0.2`:

1. A guarded tool-dispatch surface alongside command, file, and HTTP enforcement.
2. Config-driven built-in policy packs instead of only hard-coded rule values.
3. Structured audit export suitable for local inspection and regression testing.
4. A log-only workflow that is usable for real agent trial runs.
5. CI checks that run tests, build the package, and validate distributions.

## Why 0.0.2 Should Stay Narrow

The temptation after `0.0.1` is to jump to framework-specific integrations or broader deployment models.

That would be premature.

The next version should still focus on the common runtime surfaces that every future adapter will depend on:

- tool dispatch
- command execution
- sensitive file access
- outbound HTTP
- audit and decision flow

If those interfaces are not stable, every framework adapter will inherit churn.

## 0.0.2 Work Packages

### 1. Guarded Tool Dispatch

Add a first-class tool execution wrapper and corresponding event shape.

Minimum goal:

- normalize tool name and arguments
- evaluate before tool execution
- audit the decision
- preserve the ability to run in `log-only`

### 2. Config-Driven Policy Packs

Move built-in rules toward explicit configuration instead of fixed values inside rule classes.

Minimum goal:

- trusted host lists from config
- sensitive path patterns from config
- dangerous command patterns from config
- named policy packs such as `default` and `strict`

### 3. Structured Audit Output

Upgrade local audit support so decisions can be inspected and compared across runs.

Minimum goal:

- serializable audit entries
- JSON-friendly event and decision output
- simple export or snapshot helpers

### 4. Regression Fixtures

Create a small attack-fixture suite that acts as a behavioral contract for the runtime firewall.

Minimum goal:

- prompt cases
- command cases
- file cases
- HTTP cases
- expected decision for each case

### 5. CI And Release Hygiene

Lock in fast feedback for every change.

Minimum goal:

- run tests on every push
- build sdist and wheel in CI
- run `twine check`
- fail fast on packaging regressions

## 0.0.2 Non-Goals

Do not make these part of `0.0.2`:

- sidecar or proxy deployments
- broad multi-framework support
- skill trust scoring or static package analysis
- heavy ML-based prompt classification
- large policy DSL design

## Exit Criteria Before 0.0.3

Do not move to the next release focus until the following are true:

1. Tool, command, file, and HTTP surfaces all use the same event and decision model.
2. At least one real local trial run works in `log-only` mode with understandable audit output.
3. The built-in policy pack can be configured without editing source code.
4. CI reliably catches test, build, and distribution regressions.

The `0.0.2` work met that bar, but review of the implementation surfaced three semantic gaps that should be closed before framework adapters become the next focus.

## Current Assessment After 0.0.2

`0.0.2` made the runtime surfaces more uniform, but it still leaves three adapter-risking weaknesses:

1. `review` exists as a decision, but it does not yet behave like a first-class approval gate by default.
2. Outbound request validation still needs to reject malformed or unsupported URLs before host trust rules run.
3. The tool-call contract still needs to represent positional and keyword arguments cleanly for real runtime adapters.

That means `0.0.3` should still be a semantics-hardening release, not an adapter release.

## 0.0.3 Milestone

The recommended next milestone is `0.0.3` as a semantic hardening release.

The purpose of `0.0.3` is to make the current runtime firewall behavior trustworthy enough that future framework adapters inherit the right semantics instead of the current edge cases.

Definition of done for `0.0.3`:

1. `review` interrupts execution by default on enforced surfaces unless the runtime explicitly disables that behavior.
2. Built-in outbound request rules block unsupported schemes and missing hostnames before trust-list evaluation.
3. Tool-call events and the guarded tool dispatcher support both positional arguments and keyword arguments.
4. Demo, README, and regression tests all reflect the new review and network semantics.
5. The public package surface exports the new review-handling primitive cleanly.

## Why 0.0.3 Still Comes Before Adapters

It would be easy to start a LangGraph or OpenAI Agents adapter immediately after `0.0.2`.

That would lock unstable semantics into every adapter.

`0.0.3` should first make these contracts explicit and reliable:

- what `review` means operationally
- what counts as a valid outbound request
- how tool inputs are represented across runtimes

Only after those contracts are stable should adapter work become the primary release focus.

## 0.0.3 Work Packages

### 1. Approval-Gated Review Semantics

Make `review` a real execution outcome, not just a label.

Minimum goal:

- raise a dedicated review exception on enforced surfaces by default
- keep `log-only` mode non-blocking
- preserve an explicit escape hatch for runtimes that intentionally want passive review behavior

### 2. Hardened Outbound Request Validation

Tighten the outbound-request contract before trust-list checks.

Minimum goal:

- reject unsupported URL schemes
- reject requests with missing hostnames
- keep trusted-host evaluation as a second step after basic URL validity

### 3. Adapter-Ready Tool Invocation Contract

Make the tool-call surface match how real runtimes invoke tools.

Minimum goal:

- represent positional arguments separately from keyword arguments
- keep backward compatibility for the early `arguments={...}` preview API
- ensure guarded tool dispatch can pass through both forms cleanly

### 4. Demo, Docs, And Regression Alignment

Make the public story match the runtime behavior precisely.

Minimum goal:

- show review-required execution in the demo
- document that `review` pauses execution on enforced surfaces
- add regression coverage for review gating and malformed outbound requests

## 0.0.3 Non-Goals

Do not make these part of `0.0.3`:

- broad framework adapter work
- sidecar or proxy deployment patterns
- approval UI or centralized review platform work
- large policy DSL expansion
- ML-heavy prompt risk scoring

## Exit Criteria Before 0.0.4

Do not move to the next release focus until the following are true:

1. `review` decisions can no longer silently execute in the default enforcers.
2. Malformed or non-HTTP outbound URLs are blocked by the built-in policy packs.
3. Tool dispatch can represent positional and keyword arguments without ad hoc runtime-specific workarounds.
4. Demo, README, and tests all describe the same runtime behavior.

Once those conditions are met, `0.0.4` can focus on the first real runtime adapter.

## Recommended Build Order

To keep the first version robust and fast to iterate on, development should happen in this order:

1. Stabilize the normalized runtime event model.
2. Stabilize the decision and policy interfaces.
3. Add audit recording for every evaluated event.
4. Add one enforcement surface at a time.
5. Add built-in rules only after the event shape is clear.
6. Add framework adapters only after low-level enforcement is proven.

This keeps the foundation small while still making the system usable early.

## What To Build First

For the first useful preview, prioritize:

- command execution controls
- sensitive file access controls
- outbound HTTP controls
- prompt review rules for obvious instruction override attempts

Do not start with:

- sidecar or proxy deployments
- static skill scanning
- a large policy DSL
- broad multi-framework support
- full platform or UI concerns

## Testing Strategy

Early testing should use four layers:

1. Unit tests for rules and policy decisions.
2. Integration tests for guarded execution surfaces.
3. Golden attack cases for prompts, commands, files, and outbound requests.
4. Real local trial runs in `log-only` mode before default blocking.

`log-only` should be the default validation approach for real agent traffic until false positives are understood.

## Development Cadence

The recommended cadence is:

1. Build a narrow capability.
2. Add tests for both benign and malicious cases.
3. Run it in `log-only` mode against a real or demo agent.
4. Tighten rules only after observed results are understood.
5. Expand to the next execution surface.

This is more robust than trying to design the entire runtime firewall in advance.

## Non-Goals For Early Versions

- replacing sandboxing
- replacing IAM or network policy
- guaranteeing that a skill or package is safe before installation
- solving every supply-chain security problem around agent ecosystems
