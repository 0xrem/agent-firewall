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
