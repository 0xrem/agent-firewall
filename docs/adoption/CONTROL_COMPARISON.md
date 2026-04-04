# Control Comparison

Use this when you need a short, shareable explanation of where AgentFirewall fits relative to other controls.

## Short Version

| Control | Sees prompt and tool context | Stops side effects before execution | Best at | Main limit by itself |
| --- | --- | --- | --- | --- |
| Prompt-only guardrails | Partial | No | catching obvious unsafe intent in text | cannot stop the later shell, file, or HTTP side effect on its own |
| Sandbox | No | Partial | containing filesystem and process damage | usually does not explain which agent step caused the attempt |
| Network proxy | No | Only network | enforcing outbound egress policy | cannot see prompt or local file and shell actions |
| AgentFirewall | Yes | Yes | pre-execution decisions on prompt, tool call, shell, file, and HTTP | does not replace sandboxing, IAM, or egress controls |

## The Practical Recommendation

Do not frame this as "choose one."

The practical stack is usually:

1. prompt guardrails for early text filtering
2. AgentFirewall for runtime-side pre-execution decisions
3. sandbox and egress controls for containment and defense in depth

## When AgentFirewall Changes The Outcome

AgentFirewall matters most when the failure mode is:

- a prompt or tool output steering the agent into a dangerous tool call
- a shell step that should pause for review before running
- a local secret read that should never happen
- an outbound request to a host that is not on the trust list

That is why it fits as a runtime decision layer rather than a replacement for lower-level system controls.
