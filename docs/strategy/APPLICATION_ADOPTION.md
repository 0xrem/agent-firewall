# Application Adoption Strategy

## Purpose

This document answers two practical questions:

1. Which application scenarios should AgentFirewall target right now?
2. How does AgentFirewall widen into more applications without drifting away from the core product goal?

It is written for collaborators who need a clear product-development filter before they start building examples, integrations, evals, or new runtime support.

## Core Rule

AgentFirewall should enter applications where execution control is the product, not where it is only a nice-to-have.

That means the best-fit applications share three traits:

- the AI system can cause real side effects
- the operator needs a decision point before those side effects happen
- the team can learn from `log-only` traces before turning on hard blocking

If a new application idea does not strengthen those three traits, it is probably not a priority yet.

## Why This Does Not Drift From The Core Goal

This document does not change the product goal.

The core goal is still:

- one runtime firewall core
- shared `allow` / `block` / `review` / `log` semantics
- execution-path protection for tool-using AI systems

Application guidance is only here to answer a narrower question:

- where can that core solve painful problems today
- where should we collect product-trust evidence next

That keeps application expansion tied to the same execution model instead of turning into generic "AI app platform" work.

## What The Product Solves In Application Terms

In application language, AgentFirewall solves this:

- "My AI system can now do things, and I need a brake pedal before it does the wrong thing."

Concretely, the product is strongest when an application needs to:

- inspect prompts before execution
- intercept tool calls before they run
- review sensitive tool usage
- block dangerous shell, file, or outbound HTTP actions
- keep an audit trail that ties side effects back to the originating tool flow

## Best-Fit Application Scenarios Right Now

These are the application categories the repo should prioritize right now.

### 1. Internal Engineering Agents

Examples:

- repository analysis assistants
- code migration helpers
- CI triage or developer productivity agents
- infrastructure diagnostics tools

Why this fits now:

- they often use shell, file, and HTTP together
- the blast radius is real but still controlled enough for local demos and evals
- the user is usually technical and can adopt `log-only` first

Best current runtime path:

- LangGraph official adapter
- OpenAI Agents official adapter

High-value proof points:

- blocking dangerous shell commands
- blocking reads of secrets and credentials
- blocking outbound HTTP to untrusted hosts
- correlating nested side effects back to the originating tool call

### 2. Incident Response And Ops Automation

Examples:

- incident triage agents
- runbook assistants
- log and metrics helpers with limited remediation actions
- internal support tools for on-call engineers

Why this fits now:

- these systems need execution control more than perfect free-form conversation
- they naturally benefit from `review` and `log-only`
- the task boundaries are narrow enough to build believable local evals

Best current runtime path:

- LangGraph official adapter
- OpenAI Agents official adapter
- generic wrappers for unsupported internal runtimes

High-value proof points:

- reviewed shell access before remediation steps
- restricted network destinations
- auditable side effects during incident workflows

### 3. Controlled Back-Office Workflow Agents

Examples:

- document-processing helpers that can write files
- internal data-handling agents that call approved tools
- scheduled automation jobs with narrow operational scope

Why this fits now:

- these applications care about safe execution more than open-ended reasoning
- they can start with narrow tool sets
- they are easier to validate offline than consumer-facing assistants

Best current runtime path:

- OpenAI Agents official adapter
- generic wrappers

High-value proof points:

- reviewed file writes
- blocked access to sensitive paths
- blocked exfiltration over outbound HTTP

### 4. Security And Compliance Assistants

Examples:

- secret-scanning follow-up agents
- access-review assistants
- policy-enforcement copilots with controlled tools

Why this fits now:

- the value proposition is naturally aligned with "prevent bad side effects before they happen"
- auditability matters as much as execution
- conservative workflows tolerate explicit review steps

Best current runtime path:

- LangGraph official adapter
- OpenAI Agents official adapter

High-value proof points:

- deterministic review flows
- explainable blocked decisions
- reproducible local evidence

## Application Scenarios To De-Prioritize Right Now

These are not "never" categories.

They are just poor fits for the current maturity level.

### 1. Pure Chat Applications With No Real Side Effects

Why not now:

- the product's strongest value is execution control
- without tool execution, AgentFirewall is not the most important layer

### 2. Broad Consumer General-Purpose Assistants

Why not now:

- wide-open behavior surfaces make false-positive pressure harder to understand
- product trust is harder to build before application templates and evidence mature

### 3. Heavy Browser/RPA Automation

Why not now:

- browser control adds large new execution surfaces
- it would expand the runtime model before the current surfaces are fully productized

### 4. Hosted Tool Marketplaces Or Arbitrary Third-Party MCP Ecosystems

Why not now:

- the support boundary would outrun local evidence
- the product would start looking broader than it actually is

### 5. Fully Autonomous Background Agents With No Review Path

Why not now:

- `review` and `log-only` are part of the trust-building story
- removing them too early increases risk before the evidence base is strong enough

## Recommended Adoption Motion For Real Applications

When a team adopts AgentFirewall in an application, the preferred motion should be:

1. Start on one narrow workflow with real tools.
2. Run in `log-only` mode first.
3. Inspect the trace and audit output.
4. Turn on `review` for sensitive operations.
5. Turn on hard blocking only after the workflow is understood.

This matters because the product should feel like a progressive safety layer, not a binary all-or-nothing gate.

## What Makes An Application A Good Candidate For New Examples

A new application example is worth building if most of these are true:

- it uses real side effects
- it can run locally
- it teaches something new about `review`, `block`, or `log-only`
- it exercises an official adapter or a strategically important preview path
- it can produce deterministic evidence that belongs in evals or docs

If an example is flashy but does not add reusable evidence, it should be deprioritized.

## How AgentFirewall Broadens Into More Applications

Broad application adoption should happen in stages.

### Stage 1: Deepen The Best-Fit Categories

Goal:

- win the engineering, ops, and controlled internal-automation categories first

What to build:

- more real workflow evals
- more offline examples
- clearer `log-only` onboarding
- better default bundles for existing supported runtimes

Success signal:

- developers can see a believable path from demo to internal deployment

### Stage 2: Lower The Adoption Cost Outside Official Adapters

Goal:

- let teams try the product even when they are not on LangGraph or OpenAI Agents

What to build:

- stronger generic-wrapper onboarding
- better quickstart examples for service backends, jobs, and queue workers
- more packaged evidence for preview paths

Success signal:

- unsupported runtimes still have a credible local trial path

### Stage 3: Add MCP Preview Support

Goal:

- widen from framework-shaped adapters into protocol-shaped integrations

What to build:

- MCP client preview path
- MCP server preview path
- shared `resource_access` surface
- offline MCP evals and examples

Success signal:

- AgentFirewall can protect tool and resource flows that do not look like one specific framework

### Stage 4: Build Product Trust For Wider Application Classes

Goal:

- make the product feel safe to adopt beyond narrow internal pilots

What to build:

- benign workflow evals
- false-positive pressure suites
- application-focused examples
- clearer guidance on when to use `log-only`, `review`, and hard blocking

Success signal:

- teams can explain why something was blocked and know how to tune rollout safely

### Stage 5: Only Then Explore Broader Delivery Shapes

Goal:

- explore sidecars, shared services, or more centralized workflows only after the execution model is stable

Why later:

- broad delivery work should amplify a proven product, not hide an immature one

## Product Requirements For Wider Application Entry

To broaden application adoption honestly, the repo still needs all of the following:

### 1. Easier App-Level Onboarding

Need:

- grouped setup paths
- service-style examples
- better generic-wrapper docs

### 2. Stronger Trust Evidence

Need:

- more benign workflow coverage
- clearer false-positive expectations
- more realistic app-oriented evals

### 3. More Protocol And Runtime Reach

Need:

- MCP preview support
- continued support-inventory discipline
- no marketing claims without release-gated evidence

### 4. Better Rollout Guidance

Need:

- clear advice for `log-only`
- clear advice for when to use `review`
- clear advice for when to use hard blocking

## Collaboration Filter For New Application Work

Before building a new example, adapter, or application guide, ask:

1. Does this scenario involve real side effects?
2. Does AgentFirewall add value before the side effect happens?
3. Can the scenario run locally and deterministically?
4. Can users adopt it in `log-only` first?
5. Does it strengthen an existing supported path or a documented next milestone?

If the answer to most of these is "no", it is probably not the right next application investment.

## Recommended Near-Term Backlog For Application Adoption

These are good application-facing tasks that do not drift from the core roadmap:

- add more internal engineering workflow evals on the official adapters
- add service-style examples for backend jobs and internal automation tasks
- improve generic-wrapper onboarding for unsupported runtimes
- document rollout playbooks for `log-only` -> `review` -> `block`
- build MCP preview examples only after the shared `resource_access` surface lands

## Summary

The product is not too narrow because it lacks value.

It is narrow because it is focused on the place where execution control matters most.

The right path into wider application adoption is:

- go deep on high-pain, tool-using internal applications first
- make unsupported runtimes easier to trial safely
- widen through MCP preview without breaking the core model
- earn broader trust through evidence instead of claims

That keeps application growth aligned with the main product goal.
