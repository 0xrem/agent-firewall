# Log-Only Rollout

Use `log-only` when you want to learn how AgentFirewall sees your workflow before you let it stop anything.

## Why Start Here

`log-only` is the lowest-friction adoption path:

- developers keep their existing workflow
- security and platform teams get real audit evidence
- you can tune `trusted_hosts`, review handling, and rollout scope before enforcement

This is the recommended starting point for new integrations.

## Minimal Setup

Runtime-agnostic core:

```python
from agentfirewall import ConsoleAuditSink, FirewallConfig, create_firewall

firewall = create_firewall(
    config=FirewallConfig(name="trial-run", log_only=True),
    audit_sink=ConsoleAuditSink(),
)
```

That is enough to start observing what would normally have been reviewed or blocked.

If you want structured traces for later inspection:

```python
from agentfirewall import InMemoryAuditSink, MultiAuditSink

memory = InMemoryAuditSink()
firewall = create_firewall(
    config=FirewallConfig(name="trial-run", log_only=True),
    audit_sink=MultiAuditSink([memory, ConsoleAuditSink()]),
)
```

## What To Watch In The Audit Output

Focus on these fields first:

- event kind: `prompt`, `tool_call`, `command`, `file_access`, `http_request`
- rule name: which built-in rule matched
- `decision_metadata.original_action`: whether the event would have been `review` or `block`
- runtime context: which tool call caused the later shell, file, or HTTP side effect

In `log-only`, a trace entry often looks like:

- action=`log`
- `decision_metadata.original_action=review`

or:

- action=`log`
- `decision_metadata.original_action=block`

That tells you the workflow stayed live, but the policy still matched.

## What To Review Before Tightening

Look for repeated patterns, not one-off noise:

- shell tools that always need approval
- outbound hosts that are legitimate for your app but not yet trusted
- file paths that are intentionally accessed by your workflow
- prompt phrases that are coming from test corpora, docs, or mirrored content

If the same legitimate action keeps landing in `log`, fix the policy or the integration before you turn on enforcement.

## When To Move To `review`

Move from `log-only` to `review` when:

- you have identified the legitimate outbound hosts your app really uses
- the team understands the audit output and can explain the common matches
- you want humans to approve high-risk actions such as shell access

Typical next step:

```python
from agentfirewall import FirewallConfig, create_firewall
from agentfirewall.approval import TerminalApprovalHandler

firewall = create_firewall(
    config=FirewallConfig(name="trial-run"),
    approval_handler=TerminalApprovalHandler(),
)
```

## When To Move To `block`

Move from `review` to stronger blocking when:

- the audited workflow has stabilized
- the approval path is clear and deterministic
- you have tuned `trusted_hosts` and any custom review logic
- you know which actions should never proceed in your environment

For CI, regression tests, or deterministic demos, `approve_all()` is useful. For a real rollout, it is usually the wrong long-term default.

## Common Mistakes

- turning on blocking before you have looked at a representative audit sample
- leaving `trusted_hosts` at the default when your app depends on other legitimate domains
- treating `approve_all()` as a production approval strategy
- ignoring runtime-context correlation, which is often the fastest way to tell whether a later file or HTTP event came from the expected tool call
- assuming generic preview support means full official runtime support

## Useful Next Steps

- fit check: [`WHO_SHOULD_USE.md`](./WHO_SHOULD_USE.md)
- false-positive guide: [`../trust/FALSE_POSITIVES.md`](../trust/FALSE_POSITIVES.md)
- policy tuning: [`../trust/POLICY_TUNING.md`](../trust/POLICY_TUNING.md)
- local demo: [`../../examples/log_only_rollout.py`](../../examples/log_only_rollout.py)
