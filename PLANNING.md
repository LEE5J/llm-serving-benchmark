# Planning Notes

> Audience: planning and review agents.
>
> Coding agents should implement from `SPEC.md`. This file records intent,
> tradeoffs, rejected approaches, and future planning. When a decision becomes a
> requirement, copy the concise rule into `SPEC.md`.

## Document Roles

- `README.md`: why the project exists and how to use it
- `SPEC.md`: minimum implementation contract for coding agents
- `PLANNING.md`: design memory for planning and review agents

The previous SPEC was too long because it mixed all three roles. The current
SPEC should stay close to the minimum needed for spec-driven development.

## Current Product Intent

The benchmark should help a user decide which serving framework fits their own
hardware, model, and deployment constraints.

This is not a fixed-hardware leaderboard. Hardware is part of the result context.
A framework that wins on one GPU, memory budget, quantization mode, or CPU/GPU
mix may not win elsewhere.

Planning decision:

- standardize method, request schema, metric names, and artifact schema
- record hardware and software environment
- do not require one standard hardware baseline

## Agent Separation

Planning agent responsibilities:

- understand user intent
- choose architecture and branch slicing
- record rationale and tradeoffs here
- update `SPEC.md` only when a decision becomes an implementation contract
- review coding-agent output against `SPEC.md`

Coding agent responsibilities:

- read `SPEC.md`
- implement one branch slice
- write or update tests for that slice
- avoid broad design changes
- run required verification

## Why The Current Scope Is Performance Only

Quality benchmarks are important, but they introduce dataset licensing, scoring,
answer extraction, prompt template, and sandbox concerns. The performance harness
should be stable first because quality runners will reuse its schemas, metadata,
reporting, and client patterns.

Do not add quality benchmark implementation until the current performance harness
contract is reviewed.

## Module Boundary Rationale

`schemas` first:

- shared contract for all other modules
- prevents each branch from inventing different raw/summary fields

`metrics` without I/O:

- deterministic and easy to test
- no live server required

`openai_client` sends one request:

- TTFT timing is sensitive
- scheduling belongs in `workloads`

`workloads` owns scheduling:

- closed-loop concurrency is benchmark semantics
- fake async clients can test it without network

`reporting` owns artifacts:

- raw failures must not be dropped
- CSV and JSON summaries must stay equivalent

`resources` is optional:

- hardware metadata matters
- missing GPU tools must not break local development or CI

`cli` only wires modules:

- avoids turning CLI into the place where benchmark semantics are hidden

## Branch Strategy

Recommended merge order:

1. schemas
2. metrics
3. reporting
4. openai client
5. workloads
6. resources
7. CLI/config integration

Reason:

- schemas unblock everyone
- metrics and reporting are easy to test early
- client and workloads can proceed independently after schemas
- CLI integration should wire stable modules

Each branch should include tests and implementation together. Long-lived
test-only branches create noisy failures and are harder to merge.

## Protected Semantics

Do not change these without updating `SPEC.md` and recording the reason here:

- closed-loop means fixed in-flight workers, not open-loop RPS
- warmup uses the same path as measured requests and is excluded from artifacts
- TTFT is client-observed from streaming responses
- TPOT uses the SPEC formula
- goodput is useful SLO-satisfying work, not raw throughput
- every measured failure is preserved in raw JSONL
- hardware is captured as metadata, not treated as a required standard

## Deferred Planning Questions

- exact percentile interpolation method for official reports
- tokenizer abstraction and model-specific tokenizer loading
- open-loop arrival mode and RPS sweeps
- quality benchmark dataset loader structure
- synthetic long-context generation policy
- HumanEval/MBPP sandbox design
- framework-native metrics integration
- report comparison rules across different hardware
