#!/usr/bin/env bash
set -euo pipefail
MODEL_PATH=${1:?usage: servers/llama_cpp.sh /path/to/model.gguf [port]}
PORT=${2:-8002}
HOST=${HOST:-0.0.0.0}

llama-server   --model "$MODEL_PATH"   --host "$HOST"   --port "$PORT"   --ctx-size 4096
