# Changelog

## 1.2.0 - 2026-03-14

Second official adapter release. OpenAI Agents SDK now joins LangGraph as an official, release-gated AgentFirewall adapter on a deliberately narrow `function_tool`-first boundary.

### New capabilities

- Promoted `agentfirewall.openai_agents` into the official adapter registry with shared conformance validation, packaged eval expectations, and release-gate coverage.
- Expanded the OpenAI Agents adapter contract to declare official guarded shell, file-read, file-write, and outbound HTTP helper surfaces alongside prompt and tool-call interception.
- Updated the runtime support inventory so `openai_agents` now exports as an official adapter while `generic_wrappers` remains the preview runtime path.
- Added official-adapter regression coverage for OpenAI Agents release gates, runtime-context requirements, file-write evidence, and log-only semantics.

### Documentation and release evidence

- Updated README, supported-path, product-status, roadmap, and adapter-capability docs for the `1.2.0` support contract.
- Refreshed the runtime support manifest so docs and GitHub Pages can reflect the new two-adapter shipping position.
- Recorded the `1.2.0` release-readiness position with LangGraph and OpenAI Agents as the two official runtime adapters.

## 1.0.0 - 2026-03-12

Stable release. The LangGraph runtime path is the officially supported 1.0.0 adapter.

### New capabilities

- **Expanded prompt injection detection** from 3 to 37 patterns — covers instruction override, system prompt extraction, jailbreak, DAN, mode switching, and common jailbreak phrasing.
- **Expanded dangerous command blocking** from 6 to 28 patterns — covers `curl|bash`, `chmod 777`, fork bomb, `shutdown`, `shred`, disk destruction, and more.
- **Expanded sensitive file protection** from 4 to 27 path tokens — covers `.ssh/*`, `.npmrc`, `.pypirc`, `.netrc`, `.git-credentials`, `.docker/config.json`, `.kube/config`, `/etc/shadow`, `credentials.json`, `secrets.yaml`, and more.
- **Added `ConsoleAuditSink`** — prints every firewall decision to stderr as it happens, so developers can see the firewall working in real-time during development.
- **Added `MultiAuditSink`** — fan out audit entries to multiple sinks simultaneously (e.g. console + in-memory + file).
- **Added `TerminalApprovalHandler`** — interactive terminal prompt that asks the user to approve or deny review-required actions. Prints event details and accepts y/n input. Default deny for safety.
- **Added `create_file_writer_tool`** — guarded file write tool for LangGraph agents, complementing the existing file reader tool. Both reads and writes to sensitive paths are now blocked.
- **Added `api.anthropic.com`** to default trusted hosts alongside `api.openai.com`.
- **Fixed `trusted_hosts=()` semantics** so an empty trust list blocks all outbound hosts instead of allowing every destination.
- **Fixed `create_file_writer_tool(writer=...)`** so custom writer callbacks receive `(path, content, **kwargs)` after firewall enforcement.

### Documentation and quality

- Rewrote README (English and Chinese) with quickstart showing `ConsoleAuditSink`, `TerminalApprovalHandler`, and all guarded tools including file writer.
- Added "See It In Action" section with before/after comparison and live console output example.
- Added regression tests covering expanded rules, `ConsoleAuditSink`, `MultiAuditSink`, `TerminalApprovalHandler`, trust-list semantics, and custom file writer behavior. Test count: 56 → 77.
- Removed all alpha/preview language from source code, docstrings, and documentation.
- Added `examples/attack_scenarios.py` with six concrete scenarios (including file write blocking) with audit trails.
- Updated all examples to use `ConsoleAuditSink` for real-time visibility and `create_file_writer_tool` for file write protection.
- Expanded trial runner from 9 to 10 scenarios (added credential injection via file write).
- Updated the attack-scenario demo to reuse the active Python interpreter and added it to source distributions.
- Updated CI to use pytest across Python 3.10–3.13 with attack scenario demo and eval suite as CI steps.
- Updated package classifier from Alpha to Production/Stable.

## 0.1.0a1 - 2026-03-12

- Narrowed the alpha-facing root API to core firewall construction and moved the supported runtime path behind `agentfirewall.langgraph`.
- Added `agentfirewall.approval.StaticApprovalHandler` plus shorthand helpers as the documented alpha approval path for demos, evals, and simple integrations.
- Added official guarded LangGraph tool factories for shell, outbound HTTP, and file reads so one firewall instance can protect both middleware events and tool side effects.
- Added correlated runtime-context metadata so guarded shell, HTTP, and file events can be linked back to the originating LangGraph tool call.
- Expanded audit summaries so local trials and evals now break results down by source and tool name.
- Added `log-only` workflow coverage to the LangGraph eval and trial paths, including preserved `original_action` metadata in trace output.
- Expanded the packaged LangGraph eval suite from 6 to 17 task-oriented local cases and added explicit event-sequence assertions to the JSON output.
- Expanded the LangGraph demos and trial runner to exercise guarded shell, HTTP, and file flows on the supported path, including 9 ordered task-oriented workflow traces with tool-call correlation.
- Added an explicit supported-alpha path document so the quick start, approval path, local validation commands, and support boundary live in one place.
- Added a release-readiness document that captures the `0.1.0a1` supported contract, validation evidence, known limits, and publish checklist.

## 0.0.5 - 2026-03-12

- Added an explicit approval-hook contract so reviewed actions can be approved, denied, or timed out without relying only on exceptions.
- Added a packaged LangGraph eval suite with benign and adversarial cases plus JSON-friendly result summaries.
- Added approval-path coverage to unit and LangGraph integration tests.
- Expanded the LangGraph demo to show both review-required and approval-resolved tool flows.

## 0.0.4 - 2026-03-12

- Added the first official LangGraph adapter via `create_firewalled_langgraph_agent`.
- Added `LangGraphFirewallMiddleware` to route prompt inspection and tool calls through AgentFirewall.
- Added a local LangGraph demo that runs without an external API key by using a fake tool-calling model.
- Added LangGraph integration tests and a dedicated CI job for the optional runtime extra.

## 0.0.3 - 2026-03-12

- Made `review` an approval-gated runtime outcome by default via `ReviewRequired`.
- Hardened outbound request validation to block unsupported schemes and missing hostnames before host trust checks.
- Expanded the tool-call contract to preserve positional and keyword arguments across guarded dispatch.
- Updated the demo, regression fixtures, and docs to reflect the new runtime semantics.

## 0.0.2 - 2026-03-12

- Added config-driven built-in policy packs for `default` and `strict` modes.
- Added structured audit export, including JSON-friendly snapshots and a JSONL sink.
- Added guarded tool dispatch alongside command, file, and HTTP enforcement helpers.
- Added CI coverage for tests, package builds, and `twine check`.

## 0.0.1 - 2026-03-12

- Shipped the first installable runtime-firewall preview for Python agent runtimes.
- Introduced the initial event model, decision model, and audit recording flow.
- Added guarded subprocess, file, and HTTP helpers with a runnable demo.
