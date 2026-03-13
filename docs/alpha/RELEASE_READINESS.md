# 1.0.0 Release Readiness

This file records the release-readiness state for `1.0.0`.

## Release Position

`main` is released as `1.0.0`, the first stable release for the supported LangGraph path.

That means:

- the supported public surface is intentionally narrow
- the supported runtime path is `agentfirewall.langgraph`
- approval is documented through `agentfirewall.approval`
- eval and trial evidence are strong enough for production usage on the LangGraph path

It does not mean:

- production-ready false-positive tuning beyond the default policy pack
- a second official runtime adapter
- a reviewer UI or centralized approval service

## Supported Contract

The supported `1.0.0` path is:

- `agentfirewall` for core firewall construction
- `agentfirewall.langgraph` for the supported LangGraph runtime path
- `agentfirewall.approval` for documented deterministic approval helpers

See [SUPPORTED_PATH.md](./SUPPORTED_PATH.md) for the import-level contract.

## Validation Snapshot

Validated on Python 3.10, 3.11, 3.12, 3.13.

Commands:

```bash
source venv/bin/activate
python examples/attack_scenarios.py
python examples/langgraph_quickstart.py
python examples/langgraph_agent.py
python examples/langgraph_trial_run.py
python -m agentfirewall.evals.langgraph
python -m pytest tests/ -v
python -m build --no-isolation
python -m twine check dist/agentfirewall-1.0.0.tar.gz dist/agentfirewall-1.0.0-py3-none-any.whl
```

Observed results:

- 6 attack scenarios run with full audit trails (including file write blocking)
- local quick start runs on the supported LangGraph path with all guarded tools
- local LangGraph demo exercises review, approval, and guarded side effects (read + write)
- local trial runner covers 10 task-oriented workflows
- packaged LangGraph eval suite covers 17 task-oriented cases
- eval summary is 17 passed / 0 failed
- eval status counts are 8 completed, 7 blocked, and 2 review_required
- 82 unit and integration tests pass across Python 3.10–3.13
- sdist and wheel build cleanly
- `twine check` passes

## Why This Is 1.0.0

The current repo state has:

- one documented and supported runtime adapter with full coverage
- one documented and deterministic approval path
- repeatable eval evidence with task-oriented workflow coverage
- repeatable local trial evidence with multi-step traces
- clear runtime-context correlation from guarded side effects back to the triggering tool call
- a narrow enough public API to carry forward without surface resets
- CI validation across Python 3.10–3.13
- 6 local attack scenarios demonstrating real-world protection

## Known Limits

- the supported runtime path is LangGraph only
- approval is callback-driven or static-helper-driven, not a reviewer product
- the current evidence path is local and fake-model-based
- false-positive tuning will benefit from user feedback

## Publish Checklist

- [x] Version metadata set to `1.0.0`
- [x] Package classifier set to Production/Stable
- [x] Supported contract documented
- [x] Release-readiness notes updated
- [x] README updated with effect showcase
- [x] Attack scenarios demo validated
- [x] Local quick start path validated
- [x] Task-oriented trial runner validated
- [x] Packaged eval suite validated (17/17 passed)
- [x] Test suite green on Python 3.10–3.13
- [x] Build and `twine check` green
- [x] CI pipeline covers all validation steps
