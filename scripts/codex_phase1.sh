#!/usr/bin/env bash
set -euo pipefail

# Launch Codex CLI for the Phase 1 performance harness task.
# Usage:
#   scripts/codex_phase1.sh
#
# Prerequisites:
#   - codex CLI installed and on PATH
#   - codex login completed, or OPENAI_API_KEY configured
#   - run from anywhere inside this repository

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found on PATH" >&2
  echo "Install with: npm install -g @openai/codex" >&2
  exit 1
fi

PROMPT=$(cat <<'PROMPT_EOF'
You are the coding-specialized agent for this repository.

Read these files first:
- AGENTS.md
- SPEC.md
- docs/plans/phase-1-performance-harness.md
- benchmark/bench_openai.py
- pyproject.toml

Implement Phase 1 only, following docs/plans/phase-1-performance-harness.md and SPEC.md.

Hard constraints:
- Do not implement dataset quality benchmarks yet.
- Do not add credentials or local secrets.
- Keep the existing llm-bench entrypoint working.
- Add tests for metric/schema logic.
- Run verification commands before finishing.

When done, summarize:
- files changed
- tests run and results
- known limitations
- smoke benchmark command
PROMPT_EOF
)

# Use ~/.codex/config.toml by default. This lets the user control Pro model,
# sandbox mode, approval policy, and network access directly from Codex config.
# Optional overrides:
#   CODEX_MODEL=<model-id> ./scripts/codex_phase1.sh
#   CODEX_SANDBOX=workspace-write ./scripts/codex_phase1.sh
#   CODEX_APPROVAL=on-request ./scripts/codex_phase1.sh
ARGS=(exec)
if [[ -n "${CODEX_MODEL:-}" ]]; then
  ARGS+=(--model "$CODEX_MODEL")
fi
if [[ -n "${CODEX_SANDBOX:-}" ]]; then
  ARGS+=(--sandbox "$CODEX_SANDBOX")
fi
if [[ -n "${CODEX_APPROVAL:-}" ]]; then
  # codex exec does not expose --ask-for-approval in this CLI version;
  # use the config override mechanism instead.
  ARGS+=(-c "approval_policy=\"$CODEX_APPROVAL\"")
fi
ARGS+=("$PROMPT")

codex "${ARGS[@]}"
