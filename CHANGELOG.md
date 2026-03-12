# Changelog

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
