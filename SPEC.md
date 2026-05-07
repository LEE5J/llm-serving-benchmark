# LLM Serving Benchmark SPEC

> Audience: coding agents.
>
> This file is the implementation contract for the current work. Keep it short,
> testable, and unambiguous. Planning rationale and rejected ideas belong in
> `PLANNING.md`, not here.

## Goal

Build an OpenAI-compatible LLM serving benchmark harness that can run on the
user's own hardware and produce reproducible performance artifacts.

The benchmark is hardware-aware, not hardware-standardized. It must record the
runtime environment because the best serving framework can change by GPU, CPU,
memory, driver, model, quantization, and server configuration.

## Non-Goals

Do not implement these in the current scope:

- quality benchmark datasets or scoring
- judge-based evaluation
- open-loop RPS sweeps
- distributed multi-node orchestration
- a leaderboard that assumes one standard hardware baseline
- framework-specific shortcuts that change benchmark semantics

## Supported Server API

The harness must target OpenAI-compatible chat completion servers.

Required endpoint:

- `POST /chat/completions`

Required request behavior:

- use streaming responses
- support `model`, `messages`, `max_tokens`, `temperature`, and optional stop
  sequences
- merge prompt-level `extra` fields into the request payload
- measure timings from the client perspective

## Prompt Input

Prompt files are JSONL. Each non-empty line is one JSON object.

Accepted fields:

- `id`: optional stable prompt id; default is `prompt-{line_index}`
- `prompt`: optional plain user prompt
- `messages`: optional OpenAI chat messages
- `length_profile`: optional `SS`, `SL`, `LS`, `LL`, `MIXED`, or `unknown`
- `expected_output_tokens`: optional integer metadata
- `extra`: optional object merged into the OpenAI request payload

Rules:

- Each row must contain either `messages` or `prompt`.
- If only `prompt` is present, convert it to one user message.
- Invalid JSONL must fail before network requests start.
- Prompt loading must be deterministic.

## Workload Semantics

Implement closed-loop concurrency.

Closed-loop means a fixed number of workers keep at most `concurrency` requests
in flight. When a worker completes one request, it immediately sends the next
request until the measured request target is reached.

Required concurrency presets:

- `1` with workload type `single_user`
- `10` with workload type `concurrency_10`
- `100` with workload type `concurrency_100`

The CLI may accept other positive concurrency values, but the three presets above
must work.

Warmup rules:

- warmup requests use the same request path as measured requests
- warmup results are excluded from raw JSONL and summaries
- warmup completes before measured requests start for that concurrency group

## Metrics

Compute metrics from measured requests only.

Per-request timing fields:

- `request_start_time`: Unix epoch seconds
- `first_token_time`: Unix epoch seconds or `null`
- `request_end_time`: Unix epoch seconds
- `ttft_ms`: milliseconds or `null`
- `latency_ms`: milliseconds
- `tpot_ms`: milliseconds per output token or `null`

TTFT is client-observed time from immediately before request send to the first
streamed output content token.

TPOT formula:

```text
tpot_ms = (latency_ms - ttft_ms) / max(output_tokens - 1, 1)
```

Required summary metrics:

- request throughput, req/s
- output token throughput, tok/s
- total token throughput, input + output tok/s
- TTFT mean, p50, p90, p95, p99, max
- TPOT mean, p50, p90, p95, p99
- latency mean, p50, p90, p95, p99, max
- successful requests
- failed requests
- failure rate
- goodput under SLO

Default goodput SLO:

- request succeeded
- output is non-empty
- request was not unexpectedly truncated
- `ttft_ms <= 1000`
- `tpot_ms <= 100`

Percentile behavior must be deterministic and covered by tests.

## Failure Categories

Use these exact values:

- `http_error`
- `timeout`
- `connection_error`
- `server_crash`
- `oom`
- `scheduler_rejection`
- `context_length_exceeded`
- `invalid_json_response`
- `empty_output`
- `truncated_output`
- `tokenizer_or_template_error`
- `unknown_error`

Every measured failure must appear in raw JSONL.

## Environment Metadata

Capture these fields when available. Use `null` when unavailable.

- `benchmark_project_commit`
- `run_id`
- `timestamp_utc`
- `host_name`
- `os`
- `kernel`
- `cpu_model`
- `ram_total_gb`
- `gpu_model`
- `gpu_count`
- `gpu_memory_gb`
- `nvidia_driver_version`
- `cuda_version`
- `python_version`
- `framework_name`
- `framework_version`
- `server_launch_command`
- `model_id`
- `model_revision`
- `tokenizer_id`
- `tokenizer_revision`
- `dtype`
- `quantization`
- `decoding_parameters`
- `client_command`

Missing GPU tools or CPU-only environments must not fail unit tests.

## Raw JSONL Output

Write one JSON object per measured request.

Required fields:

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
- `request_start_time`
- `first_token_time`
- `request_end_time`
- `ttft_ms`
- `tpot_ms`
- `latency_ms`
- `ok`
- `error_type`
- `error_message`
- `stop_reason`
- `raw_output_path`
- `raw_output_inline`

Required fields must be present even when the value is `null`.

## Summary Output

Write both summary CSV and summary JSON. They must contain equivalent values.

Each summary row/object must include:

- `run_id`
- `framework`
- `model`
- `workload_type`
- `concurrency`
- `length_profile`
- `total_requests`
- `successful_requests`
- `failed_requests`
- `failure_rate`
- `failure_counts_by_type`
- `request_throughput_req_s`
- `output_token_throughput_tok_s`
- `total_token_throughput_tok_s`
- `latency_mean_ms`, `latency_p50_ms`, `latency_p90_ms`, `latency_p95_ms`, `latency_p99_ms`, `latency_max_ms`
- `ttft_mean_ms`, `ttft_p50_ms`, `ttft_p90_ms`, `ttft_p95_ms`, `ttft_p99_ms`, `ttft_max_ms`
- `tpot_mean_ms`, `tpot_p50_ms`, `tpot_p90_ms`, `tpot_p95_ms`, `tpot_p99_ms`
- `slo_name`
- `good_requests`
- `request_goodput_req_s`
- `good_output_tokens`
- `token_goodput_tok_s`
- `goodput_ratio`
- environment metadata fields when available

## Module Boundaries

Target package layout:

```text
benchmark/
  __init__.py
  bench_openai.py
  cli.py
  config.py
  schemas.py
  metrics.py
  openai_client.py
  workloads.py
  reporting.py
  resources.py
```

Responsibilities:

- `schemas.py`: serializable schema objects and validation helpers
- `metrics.py`: deterministic metric math only; no I/O or networking
- `openai_client.py`: one streaming request; no concurrency scheduling
- `workloads.py`: closed-loop scheduling and prompt selection; no HTTP parsing
- `reporting.py`: raw JSONL, summary CSV, and summary JSON writers
- `resources.py`: no-op collector and optional hardware collectors
- `config.py`: CLI/config normalization and validation
- `cli.py`: orchestration only
- `bench_openai.py`: backward-compatible entrypoint

## Branch Slices

Implement one slice per branch. Each slice must include tests.

Recommended order:

1. `feat/schemas`: `benchmark/schemas.py`, `tests/test_schemas.py`
2. `feat/metrics`: `benchmark/metrics.py`, `tests/test_metrics.py`
3. `feat/reporting`: `benchmark/reporting.py`, `tests/test_reporting.py`
4. `feat/openai-client`: `benchmark/openai_client.py`, `tests/test_openai_client.py`
5. `feat/workloads`: `benchmark/workloads.py`, `tests/test_workloads.py`
6. `feat/resources`: `benchmark/resources.py`, `tests/test_resources.py`
7. `feat/cli-config`: `benchmark/config.py`, `benchmark/cli.py`, `benchmark/bench_openai.py`, and `pyproject.toml` if needed

Agents should avoid modifying files outside their assigned slice.

## Tests

Unit tests must not require a live LLM server.

Minimum tests:

- schemas: required fields, null behavior, JSON serialization
- metrics: percentile, TPOT, throughput, goodput, empty inputs
- reporting: raw JSONL, summary CSV, summary JSON in a temp directory
- client: mocked streaming response and common failure categories when practical
- workloads: fake async request function, concurrency cap, warmup exclusion,
  unique request IDs
- CLI/config: argument parsing and invalid input without network calls

Required verification before finishing:

```bash
python3 -m compileall benchmark
pytest -q
```

If package metadata changes:

```bash
python3 -m venv /tmp/llm-bench-venv
. /tmp/llm-bench-venv/bin/activate
pip install -e .
python -m compileall benchmark
```

## Backward Compatibility

- `llm-bench` must remain valid.
- `python -m benchmark.bench_openai --help` should work.
- `prompts/smoke.jsonl` must remain accepted.
- Existing `--out` and `--summary` flags must remain accepted or aliased.

## Acceptance Criteria

The current implementation scope is complete when:

- the harness runs against an OpenAI-compatible `/chat/completions` endpoint
- closed-loop concurrency presets 1, 10, and 100 work
- warmup is excluded from measured artifacts
- TTFT, TPOT, latency percentiles, throughput, goodput, and failures are reported
- raw JSONL, summary CSV, and summary JSON are produced
- environment metadata is recorded when available
- `prompts/smoke.jsonl` can be used for a smoke run
- unit tests for schemas, metrics, reporting, and scheduling exist
- `python3 -m compileall benchmark` passes
- `pytest -q` passes
