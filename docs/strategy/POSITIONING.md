# Positioning

## One-Line Position

AgentFirewall is a runtime firewall for tool-using AI systems. It stops dangerous side effects before they happen.

`1.2.0` ships with LangGraph and OpenAI Agents SDK as the two official adapters, plus documented preview runtime support for generic guarded wrappers.

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
- shared policy and audit semantics across the supported LangGraph and OpenAI Agents paths

What the product direction promises next:

- the same core model reused across more adapters
- expansion into MCP and other tool-calling runtimes without resetting semantics
- lightweight adoption paths through official adapters and generic wrappers

## Messaging Pillars

- stop side effects before execution
- keep policy and audit close to the runtime
- make risky tool use reviewable instead of opaque
- prove the model with two strong adapters, then expand without changing the core story

## Say This

- "runtime firewall"
- "tool-using AI systems"
- "LangGraph and OpenAI Agents"
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

AgentFirewall 1.2.0 is out.

If your runtime can read files, send HTTP requests, or run shell commands, prompt safety is no longer just about better instructions. It is about execution control.

AgentFirewall adds `allow` / `block` / `review` / `log` decisions before dangerous side effects happen, with LangGraph and OpenAI Agents as the two official adapters and generic wrappers as the preview fallback.

### Chinese

AgentFirewall 1.2.0 发布了。

只要你的 runtime 能读文件、发 HTTP、跑 shell，安全问题就不只是 prompt 写得好不好，而是执行边界有没有被真正守住。

AgentFirewall 会在危险副作用发生前做 `allow` / `block` / `review` / `log` 决策。现在已经有 LangGraph 和 OpenAI Agents 两条官方 adapter 路径，同时保留 generic wrappers 作为预览兜底路径，为后续 MCP 和更多 runtime 扩展打基础。

## Communication Guardrail

Lead with the current supported path.

Then explain the broader product direction.

Do not reverse that order.
