# Product Status

## Current Stage

AgentFirewall is no longer proving whether the adapter-oriented architecture is real.

`1.2.0` ships that proof:

- LangGraph is still a stable official adapter
- OpenAI Agents SDK is now the second official adapter on a narrow, documented support boundary
- the shared policy, approval, audit, conformance, and runtime-context model now spans two different runtimes

That moves the product into a new phase:

- less architecture risk
- more adoption, evidence, and product-trust work

## What The Product Can Solve Today

Today the product can reliably solve one narrow but important problem:

- stop dangerous side effects before they happen on the documented official runtime paths

More concretely, the current product can:

- inspect prompts before model execution
- intercept tool calls before execution
- review or block sensitive tool usage
- block dangerous shell commands
- block sensitive file reads and writes
- block outbound HTTP requests to untrusted hosts
- preserve audit traces that link side effects back to the originating tool call

This is now available across:

- LangGraph
- OpenAI Agents SDK
- a preview generic-wrapper path for unsupported runtimes

## Status By Product Pillar

| Pillar | Status | Notes |
| --- | --- | --- |
| Stop dangerous side effects before execution | `strong` | Shipped on both official adapters |
| Shared runtime firewall core | `strong` | Policy, approval, audit, enforcers, and runtime context are adapter-oriented |
| Adapter contract and release evidence | `strong` | Capability matrix, conformance, eval expectations, and release gates exist for both official adapters |
| Lightweight non-official adoption | `partial` | Generic wrappers exist and are documented, but onboarding can still get easier |
| Multi-runtime proof | `strong` | OpenAI Agents is now an official release-gated adapter |
| Production trust across unknown workloads | `early` | False-positive pressure and real deployment evidence still need work |

## What Is Still Hard

The hard part is no longer "can this architecture support a second runtime?"

The hard part is now proving three things:

1. New users can adopt it without feeling trapped in one framework.
2. Real workloads can run in `log-only` long enough to build trust before enforcement.
3. The default policy pack stays useful as coverage grows beyond toy demos.

Put differently:

- foundation risk is much lower than it was in `1.0.0`
- adoption friction still matters
- deployment trust still needs evidence

## Most Important Remaining Gaps

### 1. Adoption Gap

Need:

- easier onboarding outside the official adapter path
- more local examples that do not require optional runtime dependencies
- a clearer `log-only` first-run path for generic wrappers and future runtimes

Why it matters:

- a product can be technically right and still feel too hard to try

### 2. Production Proof Gap

Need:

- more false-positive pressure cases
- more real workflow evals
- more evidence from actual user tasks and failures

Why it matters:

- runtime security tools win or lose on trust, not just on architecture

### 3. Breadth-After-1.2 Gap

Need:

- a stronger generic-wrapper adoption story
- the next runtime expansion path, likely MCP-oriented
- continued discipline so broader support does not outrun evidence

Why it matters:

- `1.2.0` proves the core is reusable, but it does not yet prove broad ecosystem coverage

## Execution Order From Here

1. Hold the `1.2.0` support contract steady across LangGraph and OpenAI Agents.
2. Keep lowering adoption friction for unsupported runtimes through generic wrappers.
3. Expand evals and false-positive pressure around realistic workflows.
4. Widen into MCP-oriented preview paths only after the existing contract stays stable.
5. Explore broader deployment patterns after the event model and support boundary stop moving.

## Next Milestone

The next milestone should be `1.3` as the MCP preview and resource-surface release.

That means:

- MCP is important enough to become the next focused expansion track
- MCP is still risky enough that it should stay preview, not official, in the first release
- the main design job is to add one honest shared surface for resource reads without forking policy semantics

Developers working on the next milestone should start with [`RELEASE_1_3_PLAN.md`](./RELEASE_1_3_PLAN.md).

## What `1.2.0` Actually Shipped

The current second official adapter is OpenAI Agents SDK on a deliberately narrow scope:

- `Agent`
- local `FunctionTool`
- prompt inspection before model execution
- function-tool interception before local execution
- shared `review`, `block`, and `log-only` behavior
- runtime-context propagation into shared shell, file, and HTTP enforcers
- official guarded helper builders and a grouped runtime bundle

Still out of scope:

- hosted tools
- MCP servers
- handoffs
- `Agent.as_tool()`
- SDK-native `needs_approval` as the primary approval mechanism

Developers working on this track should start with [`OPENAI_AGENTS_ADAPTER_PLAN.md`](./OPENAI_AGENTS_ADAPTER_PLAN.md).

## What Would Mean "We Are On Track"

AgentFirewall is on track if the repo can honestly say all of the following:

- two supported adapters are stable and release-gated
- unsupported runtimes can still adopt low-level guarded wrappers safely
- the same policy and audit semantics hold across both official adapters
- real users can start in `log-only`, learn from audits, and tighten enforcement later

## What Would Mean "We Drifted"

AgentFirewall is drifting if any of these start happening:

- marketing promises broader compatibility than the evidence supports
- adapters fork the policy or approval model
- new users need too much framework-specific knowledge to adopt the product
- the product blocks too much in realistic benign workflows and we cannot explain why
