# False Positives

False positives matter because AgentFirewall sits on the execution path. The right way to reduce them is to inspect the audit output first, then tune the supported policy inputs deliberately.

## Common Review Matches

These usually show up as `review` first:

- prompt text that contains instruction-override phrases such as `ignore previous instructions`
- tool calls named like `shell`, `terminal`, `execute_command`, or `run_python`

In practice, the most common review surprise is not the policy engine. It is a tool name that correctly looks risky to the default pack.

## Common Block Matches

These usually show up as `block`:

- outbound requests to domains not listed in `trusted_hosts`
- reads or writes involving sensitive path tokens such as `.env`, `.ssh/authorized_keys`, or `.git-credentials`
- destructive shell patterns such as `rm -rf`, `curl | bash`, `mkfs`, or `dd if=`
- malformed outbound URLs or unsupported schemes

## Tune `trusted_hosts` First

For many real integrations, the first tuning change is the simplest one:

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

If your app legitimately talks to another host and it is missing from `trusted_hosts`, you will keep seeing blocks until you add it.

## Rule Problem Or Integration Problem?

Use this quick check:

- if the rule name and matched metadata clearly point at a real risky pattern, it is probably a policy match you need to tune or accept
- if the later file or HTTP event is attached to the wrong `runtime_context.tool_name`, it is more likely an integration issue
- if the same legitimate action behaves differently across demos and your app, compare the tool names and runtime-context metadata first

Good fields to inspect:

- `rule`
- `decision_metadata`
- `runtime_context.tool_name`
- `runtime_context.tool_call_id`
- `source`

## Safest Workflow For Reducing False Positives

1. Start in `log-only`.
2. Identify repeat legitimate matches.
3. Tune `trusted_hosts`, tool naming, or approval behavior.
4. Move to `review`.
5. Only then decide which cases should become hard `block`s.

## Mistakes To Avoid

- using `approve_all()` to hide a policy mismatch
- changing several policy inputs at once and losing track of what fixed the issue
- treating the generic preview path as proof that every runtime edge case is already covered
- debugging only the exception text instead of the audit trace

## Related Docs

- rollout path: [`../adoption/LOG_ONLY_ROLLOUT.md`](../adoption/LOG_ONLY_ROLLOUT.md)
- tuning guide: [`POLICY_TUNING.md`](./POLICY_TUNING.md)
- benchmarks: [`BENCHMARKS.md`](./BENCHMARKS.md)
