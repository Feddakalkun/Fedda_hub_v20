#!/bin/bash
set -euo pipefail

COMFY_PORT="${COMFY_PORT:-8199}"
COMFY_LISTEN="${COMFY_LISTEN:-0.0.0.0}"
CORS_ORIGIN="${COMFY_CORS_ORIGIN:-*}"

RESERVE_VRAM_GB="${COMFY_RESERVE_VRAM_GB:-}"
if [ -z "${RESERVE_VRAM_GB}" ]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    TOTAL_MB="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n1 | tr -d '[:space:]' || true)"
    if [[ "${TOTAL_MB}" =~ ^[0-9]+$ ]]; then
      if [ "${TOTAL_MB}" -ge 70000 ]; then
        RESERVE_VRAM_GB=6
      elif [ "${TOTAL_MB}" -ge 30000 ]; then
        RESERVE_VRAM_GB=4
      elif [ "${TOTAL_MB}" -ge 20000 ]; then
        RESERVE_VRAM_GB=3
      else
        RESERVE_VRAM_GB=1
      fi
    else
      RESERVE_VRAM_GB=1
    fi
  else
    RESERVE_VRAM_GB=1
  fi
fi

EXTRA_ARGS="${COMFY_EXTRA_ARGS:-}"
echo "[FEDDA] Starting ComfyUI on ${COMFY_LISTEN}:${COMFY_PORT} (reserve-vram=${RESERVE_VRAM_GB}GB)"

# Build argv as an array to avoid shell glob expansion (e.g. '*' becoming file names),
# which can crash ComfyUI argparse with exit code 2 under supervisord.
args=(
  --port "${COMFY_PORT}"
  --listen "${COMFY_LISTEN}"
  --enable-cors-header "${CORS_ORIGIN}"
  --preview-method auto
  --disable-auto-launch
  --reserve-vram "${RESERVE_VRAM_GB}"
)

if [ -n "${EXTRA_ARGS}" ]; then
  # Allow power-users to pass additional flags via COMFY_EXTRA_ARGS.
  # shellcheck disable=SC2206
  extra_args_array=(${EXTRA_ARGS})
  args+=("${extra_args_array[@]}")
fi

exec python3 -u /app/ComfyUI/main.py "${args[@]}"
