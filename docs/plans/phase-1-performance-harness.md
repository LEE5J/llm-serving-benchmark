# Phase 1 Performance Harness Implementation Plan

> For coding agents: implement this plan against `SPEC.md`. Keep changes small, tested, and reviewable.

## Goal

Refactor the current minimal OpenAI-compatible benchmark scaffold into a SPEC-compliant Phase 1 performance benchmark harness.

## Scope

Implement only Phase 1 from `SPEC.md`:

- OpenAI-compatible async benchmark client
- closed-loop concurrency 1, 10, and 100
- streaming TTFT measurement
- TPOT and latency percentile calculation
- raw JSONL output
- summary CSV and JSON output
- basic goodput calculation
- structured failure categories
- basic resource polling hook or interface
- unit tests for metric calculations and schemas

Do not implement dataset quality benchmarks in this phase.

## Files to inspect first

- `SPEC.md`
- `README.md`
- `AGENTS.md`
- `benchmark/bench_openai.py`
- `pyproject.toml`

## Expected final structure

The coding agent may refactor toward this structure:

```text
benchmark/
  __init__.py
  cli.py
  config.py
  openai_client.py
  workloads.py
  metrics.py
  resources.py
  reporting.py
  schemas.py
  bench_openai.py      # may remain as backwards-compatible entrypoint
tests/
  test_metrics.py
  test_schemas.py
  test_workloads.py
```

## Task 1: Add metric calculation module

Objective:

- Create deterministic, unit-tested helpers for percentiles, TTFT, TPOT, throughput, and goodput.

Files:

- Create: `benchmark/metrics.py`
- Create: `tests/test_metrics.py`

Requirements:

- Percentiles must include p50, p90, p95, p99.
- Empty inputs must not crash.
- TPOT formula:

```text
tpot_ms = (latency_ms - ttft_ms) / max(output_tokens - 1, 1)
```

- Goodput must count only successful requests that satisfy the configured SLO.

Verification:

```bash
pytest tests/test_metrics.py -q
```

## Task 2: Add schemas

Objective:

- Define explicit request-result and run-summary schemas.

Files:

- Create: `benchmark/schemas.py`
- Create or modify: `tests/test_schemas.py`

Minimum raw result fields:

- `run_id`
- `request_id`
- `framework`
- `model`
- `workload_type`
- `concurrency`
- `length_profile`
- `prompt_id`
- `input_tokens`
- `output_tokens`
- `ttft_ms`
- `tpot_ms`
- `latency_ms`
- `ok`
- `error_type`
- `error_message`
- `stop_reason`

Verification:

```bash
pytest tests/test_schemas.py -q
```

## Task 3: Refactor OpenAI client

Objective:

- Move HTTP streaming logic into a reusable client module.

Files:

- Create: `benchmark/openai_client.py`
- Modify: `benchmark/bench_openai.py` or `benchmark/cli.py`

Requirements:

- Support `/chat/completions`.
- Support streaming.
- Measure first token time from client perspective.
- Categorize common failures:
  - HTTP error
  - timeout
  - connection error
  - invalid JSON response
  - empty output
  - unknown error

Verification:

- Unit tests may mock responses if practical.
- At minimum, compile check must pass.

```bash
python3 -m compileall benchmark
```

## Task 4: Implement closed-loop workload runner

Objective:

- Implement fixed-concurrency closed-loop execution.

Files:

- Create: `benchmark/workloads.py`
- Modify: `benchmark/cli.py` or `benchmark/bench_openai.py`
- Create: `tests/test_workloads.py` if testable without network

Requirements:

- Support `--concurrency 1,10,100`.
- Keep up to N requests in flight.
- Exclude warmup results from measured results.
- Preserve request ids for measured results.
- Store workload type labels:
  - `single_user`
  - `concurrency_10`
  - `concurrency_100`

Verification:

```bash
pytest tests/test_workloads.py -q
```

## Task 5: Add reporting outputs

Objective:

- Produce raw JSONL plus summary CSV and JSON.

Files:

- Create: `benchmark/reporting.py`
- Modify: CLI entrypoint

Requirements:

- Raw JSONL: one object per request.
- Summary CSV: one row per concurrency/workload group.
- Summary JSON: same data as CSV but structured.
- Include metadata fields when supplied by CLI.

Verification:

- Add tests if practical.
- Run CLI against a mocked/local endpoint if available.

## Task 6: Add CLI polish

Objective:

- Provide a clear CLI that matches README examples.

Files:

- Create: `benchmark/cli.py`
- Modify: `benchmark/bench_openai.py`
- Modify: `pyproject.toml` if entrypoint changes

Required CLI options:

- `--base-url`
- `--api-key`
- `--model`
- `--framework`
- `--prompts`
- `--concurrency`
- `--requests`
- `--warmup`
- `--max-tokens`
- `--temperature`
- `--timeout`
- `--slo-ttft-ms`
- `--slo-tpot-ms`
- `--out`
- `--summary-csv`
- `--summary-json`

Backwards compatibility:

- Existing `llm-bench` command should keep working.

## Task 7: Final verification

Run:

```bash
python3 -m compileall benchmark
pytest -q
python -m benchmark.bench_openai --help || true
llm-bench --help
```

Then provide a final summary:

- files changed
- tests run
- any known limitations
- exact commands to run a smoke benchmark

## Commit message

Use:

```bash
git commit -m "feat: implement phase 1 performance harness"
```
