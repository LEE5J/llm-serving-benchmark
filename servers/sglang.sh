#!/usr/bin/env bash
set -euo pipefail
MODEL=${1:-Qwen/Qwen2.5-7B-Instruct}
PORT=${2:-8000}
HOST=${HOST:-0.0.0.0}
SERVED_MODEL_NAME=${SERVED_MODEL_NAME:-local_model}

python -m sglang.launch_server   --model-path "$MODEL"   --host "$HOST"   --port "$PORT"   --served-model-name "$SERVED_MODEL_NAME"   --trust-remote-code   --tp-size 1
