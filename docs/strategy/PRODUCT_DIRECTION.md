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

## Non-Goals For Early Versions

- replacing sandboxing
- replacing IAM or network policy
- guaranteeing that a skill or package is safe before installation
- solving every supply-chain security problem around agent ecosystems
