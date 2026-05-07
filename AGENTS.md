# Coding Agent Instructions

This repository is intended to be implemented by coding-specialized agents such as Codex CLI or Claude Code.

## Source of truth

Read `SPEC.md` before making changes. The SPEC is the implementation contract.

Do not rely on chat history or assumptions that are not present in repository files.

## Role split

- Hermes Agent: planning, documentation, orchestration, review, GitHub management.
- Coding agent: implementation, tests, refactoring, local verification.

Major implementation tasks should be performed by a coding agent, not directly by Hermes.

## Implementation rules

1. Follow `SPEC.md` exactly.
2. Keep changes small and reviewable.
3. Prefer test-driven development.
4. Add or update tests for any behavior change.
5. Do not silently change benchmark semantics.
6. Do not add hidden benchmark shortcuts that favor one serving framework.
7. Preserve raw result artifacts and metadata requirements from `SPEC.md`.
8. Do not commit benchmark result files unless explicitly requested.
9. Do not commit credentials, API keys, local `.env` files, or model weights.
10. Public dataset licenses must be respected. Prefer runtime downloaders and dataset hashes over vendoring datasets.

## Required verification before finishing a coding task

Run at least:

```bash
python3 -m compileall benchmark
```

If tests exist, also run:

```bash
pytest -q
```

If package metadata changes, verify installability:

```bash
python3 -m venv /tmp/llm-bench-venv
. /tmp/llm-bench-venv/bin/activate
pip install -e .
python -m compileall benchmark
```

## Git rules

- Work on a feature branch unless Hermes explicitly says to commit to `main`.
- Use descriptive commit messages.
- Do not force-push `main`.
- Include verification results in the final agent response.

## Current implementation target

The current coding task should implement the performance harness described in `SPEC.md`:

- Refactor the current OpenAI-compatible benchmark harness into small modules.
- Support closed-loop concurrency 1, 10, and 100.
- Measure TTFT, TPOT, latency percentiles, throughput, goodput, and failures.
- Produce raw JSONL and summary CSV/JSON.
- Add tests for metric calculations and schema behavior.

Do not start quality benchmark implementation until the current performance harness is reviewed.
