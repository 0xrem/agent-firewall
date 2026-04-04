# Benchmarks

This repo includes a small local overhead benchmark at [`../../scripts/benchmark_overhead.py`](../../scripts/benchmark_overhead.py).

The goal is not pseudo-precision. The goal is to give a repeatable local sense of the decision-layer cost for common allow, review, and block paths.

## What The Benchmark Measures

The script uses local fake tool and HTTP helpers:

- no real network
- no real subprocesses
- no console logging
- no disk-backed audit sink

That means the numbers isolate firewall decision-layer overhead more than end-to-end application latency.

## How To Run It

From a repo checkout:

```bash
python scripts/benchmark_overhead.py
```

The script prints a JSON payload with:

- Python version
- platform
- iteration counts
- baseline mean and p95
- guarded mean and p95
- extra mean overhead

## How To Read The Numbers

Use the output this way:

- allow-path results are the most representative steady-state cost
- review-path results include exception and approval-path interruption cost
- block-path results include exception cost, but they also skip the real side effect

So if review or block looks slower than allow, that is expected. Those paths are decision-heavy by design and prevent the later side effect from running.

## Current Repo-Local Reference

Reference run in this repo workspace:

- date: `2026-04-04`
- Python: `3.12.13`
- platform: `macOS-26.3.1-arm64-arm-64bit`
- benchmark mode: fake local helpers only, no real network, subprocess, console logging, or disk audit sink

Observed means from `python scripts/benchmark_overhead.py`:

| Case | Guarded mean | Extra mean over baseline | Reading |
| --- | --- | --- | --- |
| `allow_status_tool` | `5.45 us` | `5.37 us` | representative small allow-path tool-call overhead |
| `allow_trusted_http` | `5.92 us` | `4.01 us` | representative small allow-path HTTP overhead before real network cost |
| `review_shell_tool` | `2.69 us` | `2.63 us` | review-path decision plus exception cost, before any real shell work |
| `block_untrusted_http` | `4.20 us` | `2.27 us` | block-path decision plus exception cost, while skipping the real request |

Treat those numbers as directional, not universal. They will change with Python version, machine type, audit sink, and the exact guarded surface you benchmark.

Run the script in your own environment and treat that output as the source of truth. A checked-in number would age quickly and hide the fact that overhead depends on:

- Python version
- machine type
- whether optional runtime dependencies are installed
- which audit sink you use
- whether your code writes console or disk logs on every decision

## Rough Expectations

When you run the benchmark locally, you should generally expect:

- allow paths to land in the low-single-digit microsecond range in this repo-local setup
- block and review paths to stay in the same rough microsecond order of magnitude here, even though they record a decision and raise
- real application latency to still be dominated by model calls, network I/O, subprocess work, or file I/O rather than the firewall itself

If you want stronger evidence for your own workload, benchmark the exact guarded tools and audit sinks your app uses instead of relying only on this repo-local micro-benchmark.

## Related Docs

- false-positive guide: [`FALSE_POSITIVES.md`](./FALSE_POSITIVES.md)
- policy tuning: [`POLICY_TUNING.md`](./POLICY_TUNING.md)
- rollout path: [`../adoption/LOG_ONLY_ROLLOUT.md`](../adoption/LOG_ONLY_ROLLOUT.md)
