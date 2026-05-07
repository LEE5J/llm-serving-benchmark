# LLM Serving Benchmark SPEC

> Status: draft
>
> Primary objective: define an implementation-grade specification before coding.
>
> Implementation rule: Hermes Agent is responsible for planning, documentation, orchestration, and review. Actual coding tasks should be delegated to a coding-specialized agent such as Codex CLI, Claude Code, or another autonomous coding agent. The coding agent must implement against this SPEC, not against implicit chat context.

## 1. Purpose

This project benchmarks LLM serving frameworks under controlled but diverse conditions.

The goal is not to make one framework look good under a single favorable setup. The goal is to produce objective, reproducible, and multi-dimensional evidence about how different serving frameworks behave across realistic usage patterns.

Target frameworks include:

- vLLM
- SGLang
- llama.cpp / llama-server
- Optional later: TensorRT-LLM, Hugging Face TGI, LMDeploy, Ollama, or any OpenAI-compatible server

The benchmark must evaluate both:

1. Performance and operational behavior
   - throughput
   - TTFT
   - TPOT
   - latency percentiles
   - goodput under SLO
   - failure rate
   - resource efficiency

2. Output quality and correctness regression
   - public dataset based benchmark pass/fail
   - exact-match or rule-based scoring where possible
   - code unit-test based scoring where applicable
   - judge-based evaluation only as an optional higher-cost track

## 2. Design Principles

### 2.1 Avoid single-condition bias

A serving framework may perform well in one situation and poorly in another. For example:

- A framework optimized for continuous batching may excel at high concurrency but have worse single-user latency.
- A framework using aggressive quantization may show high throughput but degrade benchmark accuracy.
- A framework may produce strong output token throughput while violating TTFT or p99 latency SLOs.
- A framework may work well for short prompts but degrade on long-context prefill-heavy tasks.

Therefore the benchmark must include multiple workload types, multiple input/output length profiles, and both performance and quality measurements.

### 2.2 Standardize what should be standardized

The benchmark should standardize the following whenever possible:

- hardware
- model checkpoint
- tokenizer revision
- prompt templates
- dataset versions
- decoding parameters
- request schema
- measurement method
- warmup policy
- result schema

But the benchmark must also record framework-specific settings explicitly instead of hiding them. Framework-specific optimizations are allowed only when documented and reproducible.

### 2.3 Prefer reproducibility over leaderboard-style optimization

Every benchmark result must include enough metadata to reproduce the run:

- git commit hash of this benchmark project
- framework name and version
- model id and revision
- quantization / dtype
- hardware and driver information
- server launch command
- benchmark command
- dataset hash or version
- prompt template version
- raw per-request results
- aggregated summary

### 2.4 Do not rely on throughput alone

Throughput-only results are insufficient.

The benchmark must report:

- raw throughput
- goodput under SLO
- TTFT distribution
- TPOT distribution
- end-to-end latency distribution
- error and timeout rate
- quality benchmark scores
- resource utilization

A run with higher throughput but much worse p99 latency, high timeout rate, or lower correctness score must not be presented as simply “better”.

## 3. Required Benchmark Types

The initial benchmark suite must define exactly these three primary serving load types.

### 3.1 Type A: Single batch / single-user benchmark

Purpose:

- Measure baseline responsiveness with no meaningful batching advantage.
- Expose framework overhead, tokenizer overhead, server overhead, and first-token latency under light load.

Required settings:

- concurrency: 1
- request pattern: sequential closed-loop
- warmup: at least 5 requests or 30 seconds
- measured requests: at least 50, recommended 100 to 300

Required metrics:

- TTFT mean/p50/p90/p95/p99
- TPOT mean/p50/p90/p95/p99
- end-to-end latency mean/p50/p90/p95/p99
- request throughput
- output token throughput
- total token throughput
- failure rate
- GPU utilization average/peak
- GPU memory peak

Interpretation:

- Best for user-perceived responsiveness.
- Not sufficient for production capacity evaluation.

### 3.2 Type B: Concurrent users 10

Purpose:

- Measure small-service or internal API style concurrency.
- Show the latency/throughput balance when batching starts to matter.

Required settings:

- concurrency: 10
- request pattern: closed-loop by default
- optional additional mode: open-loop arrival-rate sweep
- warmup: at least 30 seconds or at least 30 requests
- measured requests: at least 200, recommended 500 to 1,000

Required metrics:

- all Type A metrics
- goodput under configured SLO
- timeout rate
- error type distribution
- CPU utilization
- RAM peak
- per-GPU output tokens/sec
- good output tokens/sec/GPU

Interpretation:

- Best for realistic low-to-mid traffic services.
- Shows how quickly TTFT increases once requests are batched and queued.

### 3.3 Type C: Concurrent users 100

Purpose:

- Measure high-concurrency behavior, scheduler stability, queueing, KV cache pressure, and tail latency.

Required settings:

- concurrency: 100
- request pattern: closed-loop by default
- optional additional mode: open-loop arrival-rate sweep
- warmup: at least 1 minute, recommended 1 to 3 minutes
- measured requests: at least 1,000, recommended 2,000 to 10,000
- measured duration: at least 5 minutes when possible

Required metrics:

- all Type A and Type B metrics
- p99 latency and p99 TTFT must be reported prominently
- queueing delay if available
- OOM count
- server crash count
- request rejection count
- KV cache usage if available
- GPU power draw if available
- estimated cost per 1M output tokens
- estimated cost per 1M good output tokens

Interpretation:

- Best for capacity planning and framework stress testing.
- Raw throughput must be interpreted together with goodput and p99 latency.

## 4. Input/Output Length Profiles

Each benchmark type should be run across multiple prompt length profiles. A single prompt shape is not enough.

### 4.1 SS: short input / short output

- input: 64 to 256 tokens
- output: 64 to 128 tokens
- examples: short chat, classification-like generation, quick Q&A

### 4.2 SL: short input / long output

- input: 64 to 256 tokens
- output: 512 to 1,024 tokens
- examples: writing, summarization expansion, code generation

### 4.3 LS: long input / short output

- input: 2,000 to 8,000 tokens initially
- output: 64 to 256 tokens
- examples: RAG, document QA, long-context summarization query

### 4.4 LL: long input / long output

- input: 2,000 to 8,000 tokens initially
- output: 512 to 1,024 tokens
- examples: long document analysis, report generation

### 4.5 MIXED: mixed production-like traffic

Initial default mixture:

- 50% SS
- 20% SL
- 20% LS
- 10% LL

The exact distribution must be stored in the result metadata.

## 5. Request Arrival Modes

### 5.1 Closed-loop mode

Closed-loop mode keeps a fixed number of in-flight requests. When one request completes, the client immediately sends another.

Required for initial implementation:

- concurrency 1
- concurrency 10
- concurrency 100

Advantages:

- simple
- stable
- directly comparable across frameworks

Limitations:

- does not fully model real user arrival bursts
- latency increase indirectly reduces request rate

### 5.2 Open-loop mode

Open-loop mode sends requests according to an external arrival schedule, such as fixed RPS or Poisson arrivals.

Initial status:

- optional, not required for first implementation

Future use:

- SLO capacity planning
- overload testing
- queue growth analysis

## 6. Performance Metrics

### 6.1 Request throughput

Definition:

- completed requests per second

Field name:

- `request_throughput_req_s`

### 6.2 Output token throughput

Definition:

- generated output tokens per second

Field name:

- `output_token_throughput_tok_s`

### 6.3 Total token throughput

Definition:

- input tokens plus output tokens per second

Field name:

- `total_token_throughput_tok_s`

This is required because prefill-heavy workloads can be misrepresented by output-token-only throughput.

### 6.4 TTFT: Time To First Token

Definition:

- client-observed time from request send to first streamed output token

Required statistics:

- mean
- p50
- p90
- p95
- p99
- max

Fields:

- `ttft_mean_ms`
- `ttft_p50_ms`
- `ttft_p90_ms`
- `ttft_p95_ms`
- `ttft_p99_ms`
- `ttft_max_ms`

### 6.5 TPOT: Time Per Output Token

Definition:

- average time per output token after the first token

Recommended formula:

```text
tpot = (end_to_end_latency - ttft) / max(output_tokens - 1, 1)
```

Required statistics:

- mean
- p50
- p90
- p95
- p99

### 6.6 End-to-end latency

Definition:

- client-observed time from request send to full response completion

Required statistics:

- mean
- p50
- p90
- p95
- p99
- max

### 6.7 Goodput

Goodput is the amount of useful work completed within an SLO.

Default interactive SLO:

- TTFT <= 1,000 ms
- TPOT <= 100 ms/token
- end-to-end latency p95 target <= 15,000 ms
- request completed without error
- output was not empty
- output was not invalid or truncated unexpectedly

Required fields:

- `slo_name`
- `slo_definition`
- `good_requests`
- `request_goodput_req_s`
- `good_output_tokens`
- `token_goodput_tok_s`
- `goodput_ratio`

### 6.8 Failure metrics

Failures must be categorized.

Required categories:

- HTTP error
- timeout
- connection error
- server crash
- OOM
- scheduler rejection
- context length exceeded
- invalid JSON response
- empty output
- truncated output
- tokenizer or template error
- unknown error

Required fields:

- `successful_requests`
- `failed_requests`
- `failure_rate`
- `failure_counts_by_type`

## 7. Resource Metrics

The benchmark must support collecting resource metrics during each run.

Required if available:

- GPU utilization average and peak
- GPU memory average and peak
- GPU power average and peak
- CPU utilization average and peak
- RAM average and peak
- server process RSS peak

Optional advanced metrics:

- KV cache usage
- queue length
- scheduler waiting time
- GPU memory bandwidth
- tensor core utilization
- energy per token

For NVIDIA systems, the initial implementation may use `nvidia-smi` polling. Framework-native metrics can be added later.

## 8. Cost-like Metrics

Even when no real cloud cost is supplied, the benchmark must compute normalized efficiency metrics.

Required:

- output tokens/sec/GPU
- total tokens/sec/GPU
- good output tokens/sec/GPU
- requests/sec/GPU

Optional when hourly GPU cost is configured:

- estimated cost per 1M output tokens
- estimated cost per 1M good output tokens

Optional when power metrics are available:

- joules per output token
- joules per good output token

## 9. Quality and Correctness Benchmarks

Performance benchmark results must be paired with quality/correctness checks because serving choices can affect output quality.

Potential causes of quality drift:

- quantization
- tokenizer mismatch
- chat template mismatch
- stop sequence differences
- max token truncation
- batching bugs
- prefix cache or KV cache bugs
- speculative decoding differences
- sampling implementation differences
- framework-specific logits processing

### 9.1 Common quality evaluation settings

Default settings for deterministic quality evaluation:

- temperature: 0
- top_p: 1
- top_k: disabled if possible
- seed: fixed if supported
- max_tokens: benchmark-specific and fixed
- stop sequences: benchmark-specific and fixed
- chat template: versioned and fixed
- system prompt: explicit and fixed

For each quality run, store:

- model id and revision
- tokenizer revision
- prompt template version
- dataset version/hash
- decoding parameters
- framework and version
- batch/concurrency mode
- raw model output
- extracted answer
- score

### 9.2 P0 benchmarks: first implementation

The first implementation should support these benchmark families.

#### 9.2.1 MMLU subset

Purpose:

- broad multiple-choice knowledge and reasoning regression

Initial size:

- 100 to 300 examples, stratified across subjects when possible

Scoring:

- exact match on selected option A/B/C/D
- logprob-based scoring may be added later but must not be required initially

Priority:

- P0

Reason:

- widely recognized
- automatically scorable
- low implementation complexity

#### 9.2.2 GSM8K subset

Purpose:

- math word-problem reasoning regression

Initial size:

- 100 to 200 examples

Scoring:

- extract final numeric answer
- normalized exact match

Priority:

- P0

Reason:

- catches reasoning and formatting regressions
- automatically scorable

#### 9.2.3 IFEval subset

Purpose:

- instruction-following and format-following regression

Initial size:

- about 100 examples

Scoring:

- rule-based checker

Priority:

- P0

Reason:

- useful for detecting chat template, stop sequence, and output formatting issues

#### 9.2.4 Synthetic long-context retrieval

Purpose:

- test long-context serving correctness under different context lengths

Initial context lengths:

- 4k
- 8k
- 16k
- 32k, if model and framework support it

Scoring:

- exact match of hidden key/value or needle string

Priority:

- P0

Reason:

- directly relevant to serving frameworks and KV/cache behavior
- no judge required
- dataset can be generated reproducibly

#### 9.2.5 KMMLU subset, if Korean evaluation is enabled

Purpose:

- Korean multiple-choice knowledge/regression testing

Initial size:

- 100 to 300 examples

Scoring:

- exact match on selected option

Priority:

- P0 for Korean-service scenarios, otherwise P1

### 9.3 P1 benchmarks: next expansion

#### HumanEval pass@1

Purpose:

- Python code generation quality

Scoring:

- unit tests in sandbox

Notes:

- generated code execution must be isolated
- timeouts are mandatory

#### MBPP

Purpose:

- broader Python programming tasks

Scoring:

- unit tests in sandbox

#### TruthfulQA multiple-choice

Purpose:

- factuality and misleading-question robustness

Scoring:

- multiple-choice exact match or normalized scoring

#### KLUE / KoBEST / KorQuAD subsets

Purpose:

- Korean NLU, reasoning, and reading comprehension

Scoring:

- task-specific exact match/F1/classification accuracy

#### RULER / LongBench / L-Eval subsets

Purpose:

- more realistic long-context evaluation beyond synthetic retrieval

Scoring:

- task-dependent

### 9.4 P2 benchmarks: periodic report, not CI hard gate

Judge-based benchmarks should not be the first hard gate because they are more expensive and less deterministic.

Candidates:

- MT-Bench
- AlpacaEval / AlpacaEval 2
- Korean MT-Bench-like datasets
- LogicKor-like judge-based Korean reasoning tests

Use cases:

- nightly evaluation
- weekly report
- release candidate comparison

Do not use as the only quality benchmark.

## 10. Quality Regression Policy

The project must support baseline comparison.

Baseline examples:

- model + framework + dtype + decoding config
- model + quantization + framework
- model + serving flags

Initial warning/fail thresholds:

- MMLU subset:
  - warning: -1.0 percentage point drop
  - fail: -2.0 percentage point drop

- GSM8K subset:
  - warning: -2.0 percentage point drop
  - fail: -4.0 percentage point drop

- IFEval subset:
  - warning: -2.0 percentage point drop
  - fail: -5.0 percentage point drop

- Synthetic long-context retrieval:
  - fail if success rate drops by more than 5 percentage points for any tested context length

- HumanEval:
  - warning: two fewer solved problems
  - fail: four fewer solved problems

Small subsets have high variance. The tool should support reruns before final failure decisions.

## 11. Result Artifacts

Each benchmark run must produce three artifact classes.

### 11.1 Raw per-request JSONL

One JSON object per request.

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
- `raw_output_path` or `raw_output_inline`

### 11.2 Summary CSV/JSON

One row/object per run or per run group.

Required fields:

- metadata fields
- throughput metrics
- latency metrics
- goodput metrics
- failure metrics
- resource metrics
- cost-like metrics
- quality metrics if applicable

### 11.3 Human-readable report

A Markdown report must summarize:

- environment
- model and framework settings
- benchmark matrix
- key performance findings
- quality benchmark findings
- known caveats
- reproduction commands

## 12. Metadata Schema

Every run must store at least:

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
- `server_config_hash`
- `model_id`
- `model_revision`
- `tokenizer_id`
- `tokenizer_revision`
- `dtype`
- `quantization`
- `tensor_parallel_size`
- `pipeline_parallel_size`
- `max_model_len`
- `decoding_parameters`
- `dataset_name`
- `dataset_version`
- `dataset_hash`
- `prompt_template_version`
- `client_command`

## 13. Implementation Architecture

The codebase should be implemented as small, testable modules.

Recommended package structure:

```text
benchmark/
  cli.py
  config.py
  openai_client.py
  workloads.py
  metrics.py
  resources.py
  reporting.py
  datasets/
    mmlu.py
    gsm8k.py
    ifeval.py
    long_context.py
    kmmlu.py
  scoring/
    multiple_choice.py
    numeric.py
    instruction_rules.py
    code_tests.py
  schemas.py
servers/
  sglang.sh
  vllm.sh
  llama_cpp.sh
configs/
  benchmark-matrix.yaml
prompts/
  smoke.jsonl
results/
reports/
tests/
```

The first coding agent may refactor the current minimal scaffold toward this structure.

## 14. Implementation Phases

### Phase 0: Documentation and specification

Owner:

- Hermes Agent

Deliverables:

- `SPEC.md`
- README draft
- implementation tasks suitable for coding agents

No production code should be added in this phase beyond documentation updates.

### Phase 1: Performance benchmark harness

Owner:

- coding-specialized agent

Deliverables:

- async OpenAI-compatible benchmark client
- concurrency 1/10/100 closed-loop mode
- streaming TTFT measurement
- TPOT and latency percentile calculation
- raw JSONL output
- summary CSV/JSON output
- basic resource polling
- tests for metric calculations

### Phase 2: Quality benchmark harness P0

Owner:

- coding-specialized agent

Deliverables:

- MMLU subset runner
- GSM8K subset runner
- IFEval subset runner
- synthetic long-context retrieval runner
- optional KMMLU subset runner
- answer extraction and scoring modules
- raw outputs and score summaries
- tests for scoring/normalization

### Phase 3: Report generation

Owner:

- coding-specialized agent

Deliverables:

- Markdown report generator
- comparison tables
- warning/fail gate summary
- reproduction command section

### Phase 4: Framework setup automation

Owner:

- coding-specialized agent, reviewed by Hermes

Deliverables:

- reproducible server launch scripts
- environment capture script
- framework version capture
- health checks

### Phase 5: Advanced extensions

Owner:

- coding-specialized agent

Deliverables:

- open-loop arrival mode
- RPS sweep
- HumanEval/MBPP sandboxed code evaluation
- TruthfulQA MC
- RULER/LongBench subsets
- judge-based MT-Bench/AlpacaEval integration

## 15. Coding Agent Handoff Protocol

Hermes must not directly perform major coding implementation for this project unless explicitly requested by the user.

When implementation starts:

1. Hermes prepares a focused task from this SPEC.
2. Hermes delegates the coding task to a coding-specialized agent, preferably Codex CLI or Claude Code.
3. The coding agent works inside the git repository.
4. The coding agent must write tests before or alongside implementation.
5. Hermes reviews the result for SPEC compliance.
6. A separate review pass checks code quality.
7. Only reviewed changes are committed and pushed.

Each coding-agent task must include:

- exact goal
- exact files allowed to modify
- relevant SPEC sections
- required tests
- expected commands to run
- commit message format

## 16. Acceptance Criteria for First Useful Version

The first useful version is complete when all of the following are true:

- Performance harness can run against any OpenAI-compatible endpoint.
- It supports concurrency 1, 10, and 100.
- It records TTFT, TPOT, latency percentiles, throughput, goodput, and failures.
- It produces raw JSONL and summary CSV/JSON.
- It can run at least one smoke prompt file.
- It includes at least two P0 quality benchmark runners.
- It includes a synthetic long-context retrieval benchmark.
- It has unit tests for metric calculations and answer extraction.
- README explains purpose, limitations, and quick start.
- SPEC is the source of truth for future coding-agent work.

## 17. Non-goals for Initial Version

The initial version does not need to:

- claim a universal winner among serving frameworks
- support every benchmark dataset
- support every framework-specific optimization
- implement judge-based evaluation
- implement distributed multi-node serving
- implement production dashboarding
- provide cloud cost integration

These can be added later.

## 18. Caveats

- Public dataset licenses must be verified before redistribution or committing dataset files.
- Prefer downloading datasets at runtime or storing only small generated/subset metadata when license is unclear.
- Generated model outputs may be large; raw outputs should be stored carefully and may be excluded from git.
- Client-side benchmarking can become the bottleneck; client resource usage must be monitored.
- Server and client on the same machine can distort resource measurements.
- Framework defaults are not equivalent; all non-default and relevant default settings must be recorded.
- Token counts may differ across tokenizers; use the model tokenizer when possible and record the tokenizer used.
