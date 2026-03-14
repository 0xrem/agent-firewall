# Product Status

## Current Stage

AgentFirewall is no longer in the "is this real?" stage.

It is now in the transition from `1.1` platform hardening to `1.2` multi-runtime proof.

That means:

- the first supported user path is real
- the adapter-oriented core is real enough to validate in code
- the biggest remaining gaps are adoption breadth and production proof, not whether the product idea makes sense

## What The Product Can Solve Today

Today the product can reliably solve one narrow but important problem:

- stop dangerous side effects before they happen in the supported LangGraph path

More concretely, the current product can:

- inspect prompts before model execution
- intercept tool calls before execution
- review or block sensitive tool usage
- block dangerous shell commands
- block sensitive file reads and writes
- block outbound HTTP requests to untrusted hosts
- preserve audit traces that link side effects back to the originating tool call

This is already useful for:

- repository automation
- incident triage
- internal tooling agents
- agent workflows that can actually touch shell, files, or the network

## Status By Product Pillar

| Pillar | Status | Notes |
| --- | --- | --- |
| Stop dangerous side effects before execution | `strong` | LangGraph path is shipped and regression-covered |
| Shared runtime firewall core | `strong` | Policy, approval, audit, enforcers, and runtime context are adapter-oriented |
| Adapter contract and release evidence | `strong` | Capability matrix, conformance, eval expectations, and release gate are in-repo |
| Lightweight non-LangGraph adoption | `partial` | Low-level wrappers exist, now with packaged eval evidence and preview-runtime inventory, but adoption still needs clearer onboarding |
| Multi-runtime proof | `in_progress` | OpenAI Agents preview support now has helper surfaces, eval evidence, and runtime-support inventory, but the second official adapter is not shipped or release-gated yet |
| Production trust across unknown workloads | `early` | False-positive pressure and real deployment evidence still need work |

## How Much Is Left

The hard part of "can this become a product?" is no longer the core architecture.

The hard part now is proving three things:

1. The same firewall model works outside LangGraph.
2. New users can adopt it without feeling trapped in one framework.
3. Real workloads can use it without unacceptable review noise.

Put differently:

- foundation risk is much lower than it was at `1.0.0`
- productization risk is still meaningful
- market-fit proof is still ahead of us

## Most Important Remaining Gaps

### 1. Breadth Gap

Need:

- a second official adapter
- a credible generic wrapper path for unsupported runtimes

Current status:

- the OpenAI Agents SDK now has an experimental `function_tool-first` adapter path with packaged evals, helper surfaces, and runtime-support inventory
- that candidate still needs release-gate evidence and an explicit promotion decision before it can count as the second official adapter

Why it matters:

- without this, the product still looks framework-local even if the architecture is not

### 2. Adoption Gap

Need:

- easier onboarding outside the official adapter path
- more local examples that do not require optional runtime dependencies
- a clear `log-only` first-run path

Why it matters:

- a product can be technically right and still feel too hard to try

### 3. Production Proof Gap

Need:

- more false-positive pressure cases
- more real workflow evals
- more evidence from actual user tasks and failures

Why it matters:

- runtime security tools win or lose on trust, not just on architecture

## Execution Order From Here

1. Ship `1.1.0` with the adapter contract, preview runtime boundaries, and release evidence clearly documented.
2. Turn the OpenAI Agents candidate path into a release-gated second-adapter decision, not just another experimental integration.
3. Keep making the generic wrapper path easier to use without claiming a second official adapter yet.
4. Expand evals and false-positive pressure around real workflows.
5. Only then widen into MCP-oriented paths and broader deployment patterns.

## Current Second-Adapter Candidate

The current `1.2` candidate is OpenAI Agents SDK on a deliberately narrow scope:

- `Agent`
- local `FunctionTool`
- prompt inspection before model execution
- function-tool interception before local execution
- shared `review`, `block`, and `log-only` behavior
- runtime-context propagation into shared shell, file, and HTTP enforcers

What still has to happen before that candidate becomes official:

- add release-gate expectations that are strict enough for promotion
- keep shrinking the unsupported boundary without overstating support
- prove the preview path stays stable under continued regression pressure
- make the official promotion decision explicit in docs and registry state

Developers working on this track should start with [`OPENAI_AGENTS_ADAPTER_PLAN.md`](./OPENAI_AGENTS_ADAPTER_PLAN.md).

## What Would Mean "We Are On Track"

AgentFirewall is on track if the repo can honestly say all of the following:

- one supported adapter is already stable
- unsupported runtimes can still adopt low-level guarded wrappers safely
- the second adapter reuses the same policy and audit semantics
- real users can start in `log-only`, learn from audits, and tighten enforcement later

## What Would Mean "We Drifted"

AgentFirewall is drifting if any of these start happening:

- marketing promises broader compatibility than the evidence supports
- adapters fork the policy or approval model
- new users need too much framework-specific knowledge to adopt the product
- the product blocks too much in realistic benign workflows and we cannot explain why
