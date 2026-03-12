# Trial Run Log

Use this file to capture findings from local demos, early adopter trials, and pre-alpha runtime validation.

The goal is to keep alpha-hardening inputs in the repo instead of leaving them in chat history or ad hoc notes.

## Entry Template

### YYYY-MM-DD - Runtime Name

- Version:
- Runtime:
- Policy pack:
- Approval mode:
- Scenario:
- What worked:
- False positives:
- False negatives:
- Integration friction:
- Follow-up actions:

## Initial Notes

- 2026-03-12: Local demos and LangGraph evals cover safe tool flow, review-required tool flow, approved review flow, denied review flow, timeout flow, and prompt review before model execution.

### 2026-03-12 - LangGraph / Python 3.12 Baseline

- Version: `main` after `0.0.5`
- Runtime: LangGraph local fake-model demos plus packaged eval runner
- Policy pack: `default`
- Approval mode: default review exception and explicit approve path
- Scenario: validated the repo under `pyenv` Python `3.12.13` with a rebuilt local `venv`
- What worked:
- `python examples/langgraph_quickstart.py`
- `python examples/langgraph_agent.py`
- `python -m agentfirewall.evals.langgraph`
- `python -m unittest discover -s tests -v`
- `python -m build --no-isolation`
- False positives:
- No eval regressions in the current LangGraph cases
- False negatives:
- None observed in the current local eval set
- Integration friction:
- The project previously relied on Python 3.14 in the local shell; switching to `pyenv` plus `.python-version` removed the LangChain compatibility warning path
- Follow-up actions:
- Keep using Python `3.12.13` for local development
- Continue tightening the LangGraph quick-start path and alpha-facing API

### 2026-03-12 - LangGraph Trial Runner

- Version: `main` after the Python 3.12 baseline
- Runtime: `examples/langgraph_trial_run.py`
- Policy pack: `default`
- Approval mode: mixed default review exception plus explicit approve path for one scenario
- Scenario: ran a four-scenario local workflow covering safe tool usage, reviewed shell usage, approved reviewed shell usage, and prompt review before model execution
- What worked:
- Aggregate status counts were `2 completed` and `2 review_required`
- Safe tool flow produced only `allow` audit actions
- Reviewed shell flow produced `allow + review`
- Approved shell flow produced `allow + review + allow`
- Prompt override flow produced a prompt-level `review`
- False positives:
- None observed in the current four-scenario local workflow
- False negatives:
- None observed in the current trial set
- Integration friction:
- The quick-start path needs separate fake-model sequences for safe and reviewed runs so demo output stays deterministic
- Follow-up actions:
- Keep the trial runner as a stable alpha-facing smoke path
- Expand it later with additional benign and adversarial scenarios if LangGraph coverage widens

### 2026-03-12 - Guarded LangGraph Side-Effect Tools

- Version: `main` during the `0.1.0a1` hardening cycle
- Runtime: LangGraph adapter plus official guarded shell, HTTP, and file-read tools
- Policy pack: `default` with `api.openai.com` as the trusted outbound host in local HTTP trials
- Approval mode: explicit review approval for shell, direct blocking for untrusted HTTP and sensitive file reads
- Scenario: validated that the supported LangGraph path now covers prompt inspection, tool review, guarded shell execution, guarded outbound HTTP, and guarded file reads under one firewall instance
- What worked:
- `python examples/langgraph_agent.py`
- `python examples/langgraph_trial_run.py`
- `python -m unittest tests.test_langgraph_integration -v`
- Safe guarded shell flow recorded `prompt -> review -> allow -> command`
- Untrusted outbound HTTP was blocked before the fake opener ran
- Sensitive file reads were blocked before the fake opener ran
- False positives:
- None observed in the current local guarded-tool scenarios
- False negatives:
- None observed in the current local guarded-tool scenarios
- Integration friction:
- The clearest supported LangGraph path now requires one explicit firewall instance to be shared across both the adapter and the guarded tools
- Follow-up actions:
- Keep documenting that explicit-firewall path as the primary supported route into alpha
- Expand evals so guarded shell, HTTP, and file-read flows are covered alongside the existing adapter cases

### 2026-03-12 - Packaged LangGraph Eval Expansion

- Version: `main` after guarded LangGraph shell / HTTP / file tools were added to the supported path
- Runtime: `python -m agentfirewall.evals.langgraph`
- Policy pack: `default`
- Approval mode: mixed default review exception plus explicit approve / deny / timeout outcomes for reviewed shell flows
- Scenario: expanded the packaged local eval suite so the formal alpha-facing evidence path now covers guarded shell command blocking, guarded HTTP host enforcement, and guarded file-read blocking or allow behavior
- What worked:
- The packaged eval suite now covers 11 local cases
- Observed status counts were `4 completed`, `5 blocked`, and `2 review_required`
- The eval JSON now includes per-case `audit_summary` data, including event-kind counts
- Guarded shell evals now show the extra `command` event after tool approval
- Guarded HTTP and file evals show direct `http_request` and `file_access` enforcement under the LangGraph-supported path
- False positives:
- None observed in the current packaged eval suite
- False negatives:
- None observed in the current packaged eval suite
- Integration friction:
- The supported path is now clearer, but the eval runner still uses fake local tools rather than a real external model or real network target
- Follow-up actions:
- Keep expanding eval cases around benign tool usage so false-positive pressure stays visible before alpha
- Consider adding a separate alpha-facing eval summary page or artifact once external feedback begins

### 2026-03-12 - Multi-Step LangGraph Trial Runner

- Version: `main` after the trial runner moved beyond single-step smoke cases
- Runtime: `examples/langgraph_trial_run.py`
- Policy pack: `default` with `api.openai.com` allowed for the trusted outbound step
- Approval mode: mixed default review exception plus explicit approval for the reviewed shell branch
- Scenario: validated multi-step local workflows where a supported LangGraph run can move across prompt inspection, one or more tool dispatches, and then into guarded shell, HTTP, or file side effects
- What worked:
- The trial runner now emits ordered `audit_trace` data per scenario
- A safe `status -> trusted_http` workflow completed with four `allow` actions
- An approved `shell -> trusted_http` workflow completed with `prompt -> review -> allow -> command -> tool_call -> http_request`
- A `status -> untrusted_http` workflow blocked only at the outbound network step
- A `status -> read_file(.env)` workflow blocked only at the file-access step
- False positives:
- None observed in the current multi-step local workflow set
- False negatives:
- None observed in the current multi-step local workflow set
- Integration friction:
- Multi-step fake-model flows require care so tool-call order stays deterministic and the audit trace stays readable
- Follow-up actions:
- Keep the multi-step trial runner as the primary alpha-facing local smoke path
- Add at least one multi-step eval case if the packaged eval suite needs stronger workflow realism before alpha

### 2026-03-12 - Static Approval Helper Path

- Version: `main` during the `0.1.0a1` hardening cycle
- Runtime: `examples/langgraph_agent.py`, `examples/langgraph_trial_run.py`, and `python -m agentfirewall.evals.langgraph`
- Policy pack: `default`
- Approval mode: documented `agentfirewall.approval.StaticApprovalHandler` helper with deterministic tool-level approval matching
- Scenario: replaced ad hoc lambda-based demo approval callbacks with the documented helper path and re-ran the local supported LangGraph workflows
- What worked:
- `StaticApprovalHandler` resolved reviewed shell flows cleanly in demos, evals, and the multi-step trial runner
- Audit metadata now shows the approval match source such as `tool` and the selected value such as `shell`
- The helper path stayed deterministic across repeated local runs
- False positives:
- None observed in the current helper-driven approval scenarios
- False negatives:
- None observed in the current helper-driven approval scenarios
- Integration friction:
- The helper is intentionally narrow and deterministic; anything more dynamic still requires a custom callback
- Follow-up actions:
- Keep the helper path documented as the recommended alpha approval story
- Avoid growing it into a pseudo-UI or centralized reviewer product before alpha feedback exists

### 2026-03-12 - Workflow Correlation Hardening

- Version: `main` during the `0.1.0a1` hardening cycle
- Runtime: `python -m agentfirewall.evals.langgraph` and `examples/langgraph_trial_run.py`
- Policy pack: `default`
- Approval mode: mixed default review exception plus deterministic approval for the reviewed shell branch
- Scenario: hardened the supported LangGraph path so guarded shell, HTTP, and file side effects carry runtime-context metadata that identifies the originating tool call
- What worked:
- Guarded `command`, `http_request`, and `file_access` events now include `runtime_context.tool_name` and `runtime_context.tool_call_id`
- Audit summaries now include `source_counts` and `tool_name_counts` for faster local diagnosis
- The packaged eval suite now covers 15 local cases, including multi-step `shell -> trusted_http`, `status -> blocked_http`, safe `status -> read_file -> trusted_http`, and `log-only` shell-plus-network workflows
- Trial and eval traces now show both event order and the originating tool-call link for side-effect events
- False positives:
- None observed in the current correlated workflow traces
- False negatives:
- None observed in the current correlated workflow traces
- Integration friction:
- The current correlation model is intentionally runtime-local; it explains one supported LangGraph run clearly, but it is not yet a cross-runtime trace system
- Follow-up actions:
- Keep the current trace shape stable through `0.1.0a1`
- Use real local workflows to pressure-test whether the current runtime-context fields are enough before freezing the alpha evidence path

### 2026-03-12 - Log-Only Workflow Evidence

- Version: `main` during the `0.1.0a1` hardening cycle
- Runtime: `python -m agentfirewall.evals.langgraph` and `examples/langgraph_trial_run.py`
- Policy pack: `default`
- Approval mode: `log-only` runtime mode with the standard default pack
- Scenario: validated that reviewed shell usage and blocked outbound HTTP can be observed end-to-end without interrupting the workflow
- What worked:
- `log-only` workflow runs now complete instead of raising, while trace entries preserve `decision_metadata.original_action`
- The eval suite now contains a formal `log_only_shell_then_blocked_http` case
- Trial output now shows which steps would have been reviewed or blocked before hard enforcement is enabled
- False positives:
- None observed in the current `log-only` local workflow case
- False negatives:
- None observed in the current `log-only` local workflow case
- Integration friction:
- `log-only` is useful for trialing a workflow, but it still requires the user to inspect trace metadata to understand what would have happened under enforcement
- Follow-up actions:
- Keep at least one `log-only` workflow in the alpha evidence path
- Use it as the default recommendation when validating a new LangGraph integration locally

### 2026-03-12 - Task-Oriented Workflow Hardening

- Version: `main` prepared for `0.1.0a1`
- Runtime: `python -m agentfirewall.evals.langgraph` and `python examples/langgraph_trial_run.py`
- Policy pack: `default`
- Approval mode: default review exception, deterministic static approval for shell triage flows, and `log-only` for one observability workflow
- Scenario: moved the supported LangGraph evidence path closer to real user tasks by validating repo triage, incident triage, prompt override, secret access, and exfiltration workflows instead of only isolated tool calls
- What worked:
- The packaged eval suite now covers 17 task-oriented cases and validates both final decisions and ordered event traces
- The local trial runner now covers 9 task-oriented workflows and reports both `status_counts` and `task_counts`
- Safe repo-triage flows completed across prompt, tool, file, and trusted HTTP steps
- Secret-access and exfiltration workflows were blocked only at the correct guarded boundary
- Approved shell triage flows preserved the full `tool_call -> command -> file_access/http_request` evidence chain
- False positives:
- None observed in the current local task-oriented suite
- False negatives:
- None observed in the current local task-oriented suite
- Integration friction:
- The evidence path is still fake-model-based, so real external integrations may expose different prompt or tool-call shapes during alpha
- Follow-up actions:
- Keep the current task-oriented workflows stable through `0.1.0a1`
- Use alpha feedback to decide which workflows should become permanent regression fixtures before beta
