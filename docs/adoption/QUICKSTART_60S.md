# Quickstart In 60 Seconds

Use this page if you want the shortest path from "what is this?" to "I saw it block something real."

## Fastest Repo Trial

From a repo checkout:

```bash
python -m pip install -e '.[langgraph]'
python examples/attack_scenarios.py
```

Why this is the default first run:

- no API key required
- the output is screenshot-friendly
- it shows `review`, `block`, and a benign allow path in one run

## No-Optional-Dependency Fallback

If you want the smallest install surface first:

```bash
python -m pip install -e .
python examples/log_only_rollout.py
```

That path will not show prompt inspection, but it does show the `log-only` rollout model and the audit fields you will use in a real adoption flow.

If you want a no-dependency side-by-side comparison instead:

```bash
python -m pip install -e .
python examples/without_vs_with_firewall.py
```

## What The Output Means

You should see:

- a prompt-injection case that gets reviewed before the model continues
- sensitive file access blocked before the file opens
- untrusted outbound HTTP blocked before the request leaves
- a dangerous shell command blocked before the subprocess runs

If you only need the short interpretation:

- `allow`: the action ran
- `review`: the action paused for approval
- `block`: the action never ran
- `log`: the action ran, but the firewall recorded that it would normally have been reviewed or blocked

## Install Paths

If you want to try the package outside a repo checkout:

```bash
python -m pip install agentfirewall[langgraph]
```

If you want the bundled examples and local eval commands from the repo:

```bash
python -m pip install -e '.[langgraph,openai-agents]'
```

## Next Step By Runtime

LangGraph:

```bash
python examples/langgraph_quickstart.py
```

OpenAI Agents SDK:

```bash
python -m pip install agentfirewall[openai-agents]
python examples/openai_agents_quickstart.py
```

Unsupported runtime, preview first:

```bash
python -m pip install agentfirewall
python examples/generic_preview_demo.py
```

## After The First Minute

If you want to roll this out without blocking developers on day one:

- start here: [`LOG_ONLY_ROLLOUT.md`](./LOG_ONLY_ROLLOUT.md)
- fit check: [`WHO_SHOULD_USE.md`](./WHO_SHOULD_USE.md)
- tuning and approvals: [`../trust/POLICY_TUNING.md`](../trust/POLICY_TUNING.md)
