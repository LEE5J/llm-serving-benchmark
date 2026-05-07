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

# Default to a safe sandbox: Codex can edit this workspace, but should ask before
# risky actions. Override CODEX_MODEL if you want to force a specific Pro model.
if [[ -n "${CODEX_MODEL:-}" ]]; then
  codex exec \
    --model "$CODEX_MODEL" \
    --sandbox workspace-write \
    --ask-for-approval on-request \
    "$PROMPT"
else
  codex exec \
    --sandbox workspace-write \
    --ask-for-approval on-request \
    "$PROMPT"
fi
