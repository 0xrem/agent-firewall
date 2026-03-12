# Changelog

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
