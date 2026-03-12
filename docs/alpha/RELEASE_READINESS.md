# 0.1.0a1 Release Readiness

This file records the repo-visible release-readiness state for `0.1.0a1`.

It is intentionally practical: supported path, validation evidence, known limits, and the publish checklist.

## Release Position

`main` is prepared for `0.1.0a1` as the first public alpha for the supported LangGraph path.

That means:

- the supported public surface is intentionally narrow
- the supported runtime path is `agentfirewall.langgraph`
- approval is documented through `agentfirewall.approval`
- eval and trial evidence are now strong enough to invite external alpha feedback

It does not mean:

- production-ready false-positive tuning
- a second official runtime adapter
- a reviewer UI or centralized approval service

## Supported Alpha Contract

The supported `0.1.0a1` path is:

- `agentfirewall` for core firewall construction
- `agentfirewall.langgraph` for the supported LangGraph runtime path
- `agentfirewall.approval` for documented deterministic approval helpers

See [SUPPORTED_PATH.md](./SUPPORTED_PATH.md) for the import-level contract.

## Validation Snapshot

Validated on Python `3.12.13`.

Commands:

```bash
source venv/bin/activate
python examples/langgraph_quickstart.py
python examples/langgraph_agent.py
python examples/langgraph_trial_run.py
python -m agentfirewall.evals.langgraph
python -m unittest discover -s tests -v
python -m build --no-isolation
python -m twine check dist/agentfirewall-0.1.0a1.tar.gz dist/agentfirewall-0.1.0a1-py3-none-any.whl
```

Observed results:

- local quick start runs on the supported LangGraph path
- local LangGraph demo exercises review, approval, and guarded side effects
- local trial runner covers `9` task-oriented workflows
- trial-run status counts are `5 completed`, `2 blocked`, and `2 review_required`
- packaged LangGraph eval suite covers `17` task-oriented cases
- eval summary is `17 passed / 0 failed`
- eval status counts are `8 completed`, `7 blocked`, and `2 review_required`
- full test suite passes under Python `3.12.13`
- sdist and wheel build cleanly
- `twine check` passes

## Why This Is Alpha-Ready

The current repo state now has:

- one documented and supported runtime adapter
- one documented and deterministic approval path
- repeatable eval evidence with task-oriented workflow coverage
- repeatable local trial evidence with multi-step traces
- clear runtime-context correlation from guarded side effects back to the triggering tool call
- a narrow enough public API to carry forward without another large surface reset

## Known Limits Before Beta

- the supported runtime path is still only LangGraph
- approval is callback-driven or static-helper-driven, not a reviewer product
- the current evidence path is local and fake-model-based
- false-positive tuning is still early and will need alpha feedback
- low-level modules remain available, but only the documented alpha contract should be treated as stable

## Publish Checklist

- [x] Version metadata set to `0.1.0a1`
- [x] Supported alpha contract documented
- [x] Release-readiness notes written in-repo
- [x] Local quick start path validated
- [x] Task-oriented trial runner validated
- [x] Packaged eval suite validated
- [x] Test suite green on Python `3.12.13`
- [x] Build and `twine check` green

## After Publish

The next work after `0.1.0a1` should stay focused on:

- alpha user feedback on the LangGraph path
- false-positive control on the default policy pack
- approval ergonomics
- better real-world workflow evidence
- deciding what must be stable for beta and what should remain advanced usage
