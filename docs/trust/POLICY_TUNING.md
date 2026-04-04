# Policy Tuning

This page explains the supported tuning path for `1.2.0`: named packs, `trusted_hosts`, and approval behavior.

## `default` vs `strict`

The supported built-in packs are:

| Pack | What it does | Good starting point |
| --- | --- | --- |
| `default` | reviews prompt injection and sensitive tool calls, blocks dangerous commands, sensitive file access, malformed requests, and untrusted hosts | first rollout, local demos, most teams |
| `strict` | blocks shell-like tool calls entirely, reviews file and HTTP tool usage, keeps the same built-in dangerous command and sensitive path protections underneath | tighter local hardening trials after the default pack is understood |

Examples:

```python
from agentfirewall import create_firewall

default_firewall = create_firewall(policy_pack="default")
strict_firewall = create_firewall(policy_pack="strict")
```

## Tune `trusted_hosts`

This is the most common first customization:

```python
from agentfirewall import create_firewall
from agentfirewall.policy_packs import named_policy_pack

firewall = create_firewall(
    policy_pack=named_policy_pack(
        "default",
        trusted_hosts=("api.openai.com", "api.myservice.com"),
    )
)
```

Use `trusted_hosts=()` if you want to default-deny all outbound hosts until you explicitly add them.

## Approval Handlers

The supported approval choices are:

| Handler path | When to use it | When not to use it |
| --- | --- | --- |
| `approve_all()` | deterministic tests, CI, simple demos, local smoke checks | real rollout decisions |
| `TerminalApprovalHandler()` | local development, interactive validation, understanding what the model is trying to do | unattended environments |
| custom callback | app-specific approval logic, policy integration with your own context | when you have not yet looked at the basic audit output |

### `approve_all()`

```python
from agentfirewall import create_firewall
from agentfirewall.approval import approve_all

firewall = create_firewall(
    approval_handler=approve_all(reason="Approved in CI."),
)
```

Use this when you need deterministic review outcomes for tests and demos. Do not confuse it with a production approval design.

### `TerminalApprovalHandler()`

```python
from agentfirewall import create_firewall
from agentfirewall.approval import TerminalApprovalHandler

firewall = create_firewall(
    approval_handler=TerminalApprovalHandler(),
)
```

Use this when you want to see risky actions pause in the terminal and approve or deny them manually.

### Custom Callback

```python
from agentfirewall import ApprovalResponse, create_firewall

def my_handler(request):
    if request.event.kind.value == "tool_call" and request.event.payload.get("name") == "shell":
        return ApprovalResponse.approve(reason="Allowed in this workflow.")
    return ApprovalResponse.deny(reason="Not approved.")

firewall = create_firewall(approval_handler=my_handler)
```

Use this when approval depends on your own workflow context.

## Recommended Tuning Order

1. Start with `default`.
2. Run in `log-only`.
3. Tune `trusted_hosts`.
4. Choose an approval path for reviewed actions.
5. Try `strict` only after the default pack is already understood.

## Related Docs

- rollout guide: [`../adoption/LOG_ONLY_ROLLOUT.md`](../adoption/LOG_ONLY_ROLLOUT.md)
- false positives: [`FALSE_POSITIVES.md`](./FALSE_POSITIVES.md)
- supported contract: [`../alpha/SUPPORTED_PATH.md`](../alpha/SUPPORTED_PATH.md)
