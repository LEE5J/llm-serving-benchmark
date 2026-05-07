# Architecture Notes

> Purpose: explain why the SPEC is structured the way it is.
>
> `SPEC.md` is the implementation contract. This file records design intent,
> tradeoffs, and sequencing decisions so that coding agents can implement small
> slices without relying on chat history.

## 1. Core Problem

This repository is intended to benchmark LLM serving frameworks objectively. The
hard part is not only sending requests; it is preserving benchmark semantics
while multiple agents add features in parallel.

The architecture therefore optimizes for:

- small modules with narrow responsibilities
- deterministic unit tests
- explicit artifact schemas
- clear feature branch ownership
- minimal hidden coupling between networking, scheduling, metrics, and reporting

The target coding agents may be weaker than the planning agent. They need a
contract that is specific enough to implement locally without making broad
architectural decisions.

## 2. Why SPEC and Architecture Notes Are Separate

`SPEC.md` should answer:

- What behavior is required?
- Which fields must exist?
- Which commands must pass?
- Which files should each feature branch own?

`architect.md` should answer:

- Why are modules split this way?
- Why is the merge sequence ordered this way?
- Which tradeoffs were considered?
- Which decisions should future reviewers preserve?

Keeping these separate prevents implementation agents from treating rationale as
optional behavior, while still preserving the reasoning behind the design.

## 3. Phase 1 Boundary

Phase 1 is limited to the performance harness. It intentionally excludes P0
quality benchmark implementation.

Reason:

- Performance harness correctness is foundational. Quality runners will reuse
  schemas, reporting, prompt loading, metadata, and possibly client code.
- Mixing quality datasets into the first refactor would create too many branch
  conflicts and make failures harder to attribute.
- The current code already has a minimal OpenAI-compatible performance scaffold,
  so Phase 1 can deliver value without introducing dataset licensing and scoring
  complexity.

Quality benchmark work should start after Phase 1 has been reviewed and merged.

## 4. Module Boundary Rationale

### 4.1 `schemas` first

Schemas are the shared language between all other modules. If raw result fields
or summary fields are ambiguous, every downstream module will make different
assumptions.

This is why `benchmark.schemas` is the first implementation branch after
documentation.

Expected benefit:

- Agents can build metrics, reporting, client, and workload modules against the
  same data contract.
- Reviewers can detect accidental benchmark semantic changes through tests.

Tradeoff:

- Early schemas may feel slightly verbose before all features exist.
- This is acceptable because stable artifact contracts matter more than minimal
  internal code.

### 4.2 `metrics` has no I/O

Metric calculations must be deterministic and easy to test. They should not know
about HTTP, files, CLI flags, or framework names beyond fields already present in
input records.

Expected benefit:

- Unit tests can cover most correctness risks without a live server.
- Future quality or report modules can reuse summary math.

Important decision:

- Percentile behavior must be tested explicitly. Different percentile
  definitions can produce different p99 values on small samples. The project
  should choose one deterministic method and preserve it.

### 4.3 `openai_client` sends one request only

The client module owns streaming protocol behavior for one request. It should not
own concurrency.

Reason:

- TTFT measurement depends on careful placement of timers around the HTTP stream.
- Concurrency scheduling is a separate source of complexity.
- Keeping one-request logic isolated makes it easier to mock streaming responses
  and failure cases.

Expected benefit:

- Workload tests can use fake request functions without HTTP.
- Client tests can focus on SSE parsing, timing fields, token accounting, and
  failure categories.

### 4.4 `workloads` owns scheduling

Closed-loop scheduling is benchmark semantics. It must be implemented in one
place and tested without network access.

Reason:

- A naive implementation that creates all tasks at once with a semaphore may
  cap concurrency but does not clearly express closed-loop worker behavior.
- Warmup exclusion and stable request IDs are easy to get wrong if scheduling is
  mixed into CLI code.

Expected benefit:

- Concurrency 1, 10, and 100 can be validated with a fake async client.
- Future open-loop mode can be added without rewriting HTTP code.

### 4.5 `reporting` owns artifact writing

Raw artifacts are a core reproducibility requirement. Reporting should be
centralized rather than scattered across CLI and benchmark modules.

Reason:

- Raw failures must never be dropped just because summary aggregation succeeds.
- CSV and JSON summaries must represent the same values.
- Large model outputs may need path-based storage later.

Expected benefit:

- Artifact behavior can be tested using temporary directories.
- Future report generation can reuse stable summary JSON.

### 4.6 `resources` is optional and non-blocking

Resource metrics are important, but resource tooling differs by machine.

Reason:

- A benchmark should still run on a CPU-only developer machine or in CI.
- Missing `nvidia-smi` should not make metric calculation or raw artifact
  generation fail.

Expected benefit:

- Unit tests remain portable.
- GPU-specific collection can improve over time without changing benchmark
  semantics.

### 4.7 `cli` wires modules but avoids logic

CLI code tends to become an untestable dumping ground. The SPEC requires it to
orchestrate modules instead of owning math, HTTP streaming, or reporting details.

Expected benefit:

- Lower-skill coding agents can modify one module without understanding the
  entire system.
- CLI changes are mostly argument parsing and integration tests.

## 5. Branch and Merge Strategy

The recommended sequence is:

1. Documentation and architecture
2. Schemas
3. Metrics
4. Reporting
5. OpenAI client
6. Workloads
7. CLI/config integration
8. Resources

Reason:

- Schemas unblock all other branches.
- Metrics and reporting can be implemented without network calls.
- Client and workload work are independent after schemas exist.
- CLI integration should happen after the lower-level modules are stable.

This order minimizes merge conflicts and lets each branch have meaningful tests.

## 6. Why Test and Feature Code Should Usually Share a Branch

The user considered making test code and feature code separately by function.
The chosen refinement is one branch per functional slice, containing both tests
and implementation.

Reason:

- A test-only branch can intentionally fail for a long time, which makes CI
  status noisy.
- A code-only branch can be merged without proving behavior.
- Pairing tests and implementation keeps each branch reviewable and mergeable.

Exception:

- A contract-only schema test branch may be useful when intentionally practicing
  strict TDD, but it should be short-lived and followed immediately by the
  implementation branch.

## 7. Benchmark Semantics to Protect

Future implementations must preserve these decisions unless `SPEC.md` changes:

- Closed-loop concurrency means fixed in-flight workers, not open-loop RPS.
- Warmup requests use the same code path as measured requests but are excluded
  from artifacts.
- TTFT is client-observed and requires streaming.
- TPOT excludes the first token using the formula in `SPEC.md`.
- Goodput is not raw throughput. It counts only successful useful requests that
  satisfy SLO conditions.
- Raw per-request records are required even when summary generation succeeds.
- Failure categories must be explicit; unknown failures should not be hidden.

## 8. Known Tradeoffs

### Client-side token counting

The initial scaffold uses local token counting approximations. The long-term
goal is to use the model tokenizer when possible and record tokenizer metadata.

Tradeoff:

- Local approximations are enough for smoke and harness development.
- Precise cross-framework comparisons require tokenizer consistency.

### Client-observed timings

The initial benchmark measures timings from the client perspective.

Tradeoff:

- This includes network and client overhead.
- It works uniformly across OpenAI-compatible servers.
- Server-native queueing or scheduler timings can be added later as optional
  metadata.

### OpenAI-compatible API first

The project targets OpenAI-compatible endpoints before framework-native APIs.

Tradeoff:

- This maximizes framework coverage and implementation simplicity.
- It may hide framework-specific metrics until later resource/native collectors
  are added.

## 9. Review Checklist for Future Branches

Reviewers should check:

- Does the branch modify only its assigned files?
- Does it preserve required raw and summary fields?
- Are benchmark semantics changed intentionally and documented in `SPEC.md`?
- Are tests deterministic and free of live-server requirements?
- Does `python3 -m compileall benchmark` pass?
- Does `pytest -q` pass when tests exist?
- Are benchmark result files, credentials, `.env` files, and model weights absent
  from the commit?

## 10. Future Architecture Questions

These are intentionally deferred:

- exact percentile interpolation method for large official reports if the simple
  Phase 1 method becomes insufficient
- tokenizer abstraction and model-specific tokenizer loading policy
- open-loop arrival scheduler design
- dataset downloader/cache structure for quality benchmarks
- sandbox design for HumanEval/MBPP
- framework-native metrics integration
- multi-node benchmark orchestration
