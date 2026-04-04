# Examples

Use this index to pick the shortest example that matches what you are trying to validate.

## First-Run Demos

| Example | Needs optional deps | Purpose |
| --- | --- | --- |
| [`attack_scenarios.py`](./attack_scenarios.py) | LangGraph | zero-API-key attack interception demo with clear without-vs-with framing |
| [`without_vs_with_firewall.py`](./without_vs_with_firewall.py) | No | no-dependency comparison of the same risky workflow before and after AgentFirewall |
| [`langgraph_quickstart.py`](./langgraph_quickstart.py) | LangGraph | shortest official LangGraph smoke test |
| [`openai_agents_quickstart.py`](./openai_agents_quickstart.py) | OpenAI Agents SDK | shortest official OpenAI Agents smoke test |

## Adoption And Rollout Demos

| Example | Needs optional deps | Purpose |
| --- | --- | --- |
| [`log_only_rollout.py`](./log_only_rollout.py) | No | show `log-only` behavior and how `original_action` is preserved |
| [`policy_reuse_demo.py`](./policy_reuse_demo.py) | OpenAI Agents SDK | reuse one policy pack across the generic preview path and the OpenAI Agents official path |
| [`generic_preview_demo.py`](./generic_preview_demo.py) | No | preview the low-level guarded wrapper path for unsupported runtimes |

## Deeper Validation

| Example | Needs optional deps | Purpose |
| --- | --- | --- |
| [`langgraph_trial_run.py`](./langgraph_trial_run.py) | LangGraph | multi-scenario trial run with ordered audit traces |
| [`langgraph_agent.py`](./langgraph_agent.py) | LangGraph | broader local adapter demo across all guarded tool types |
| [`openai_agents_demo.py`](./openai_agents_demo.py) | OpenAI Agents SDK | attack scenarios and official helper coverage on the OpenAI Agents path |
| [`core_runtime_demo.py`](./core_runtime_demo.py) | No | low-level core demo without a runtime adapter |

## Workflow Evidence

The packaged eval suites now include more realistic multi-step tasks, not only single rule hits:

- repo triage
- incident triage
- nested side-effect correlation
- `log-only` observation without interruption
