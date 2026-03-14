# Positioning

## One-Line Position

AgentFirewall is a runtime firewall for tool-using AI systems. It stops dangerous side effects before they happen.

`1.1.0` ships with LangGraph as the first official adapter, plus documented preview runtime support for OpenAI Agents SDK and generic guarded wrappers.

## Who It Is For Right Now

- teams building LangGraph agents with shell, file, or outbound HTTP access
- developers who want a visible approval and audit layer around risky tool use
- teams that want to start in `log-only` mode before turning on hard enforcement

## Pain In User Language

- "Prompt guardrails are not enough once the model can actually do things."
- "I need a brake pedal before my agent reads secrets, runs shell, or sends data out."
- "I want to see what would have been blocked before I enforce it in production."
- "I do not want a separate policy model for every runtime I use."

## Product Promise

What the product promises today:

- runtime decisions close to the execution path
- `allow`, `block`, `review`, and `log` before side effects happen
- shared policy and audit semantics on the supported LangGraph path

What the product direction promises next:

- the same core model reused across more adapters
- expansion into MCP and other tool-calling runtimes without resetting semantics
- lightweight adoption paths through official adapters and generic wrappers

## Messaging Pillars

- stop side effects before execution
- keep policy and audit close to the runtime
- make risky tool use reviewable instead of opaque
- start with one strong adapter, then expand without changing the core story

## Say This

- "runtime firewall"
- "tool-using AI systems"
- "LangGraph-first"
- "guarded shell, file, and outbound HTTP"
- "shared policy, approval, audit, and log-only model"

## Avoid Saying This

- "supports every agent framework today"
- "drop-in for every MCP stack today"
- "centralized approval platform"
- "production-grade false-positive tuning for every workload"
- "universal AI security layer"

## Short Launch Copy

### English

AgentFirewall 1.1.0 is out.

If your runtime can read files, send HTTP requests, or run shell commands, prompt safety is no longer just about better instructions. It is about execution control.

AgentFirewall adds `allow` / `block` / `review` / `log` decisions before dangerous side effects happen, with LangGraph as the first official adapter and documented preview runtime support showing how the same core expands without changing policy semantics.

### Chinese

AgentFirewall 1.1.0 发布了。

只要你的 runtime 能读文件、发 HTTP、跑 shell，安全问题就不只是 prompt 写得好不好，而是执行边界有没有被真正守住。

AgentFirewall 会在危险副作用发生前做 `allow` / `block` / `review` / `log` 决策。现在官方支持路径仍然是 LangGraph，同时已经把 OpenAI Agents 和 generic wrappers 这两条 preview runtime path 文档化，为后续第二个官方 adapter 铺路。

## Communication Guardrail

Lead with the current supported path.

Then explain the broader product direction.

Do not reverse that order.
