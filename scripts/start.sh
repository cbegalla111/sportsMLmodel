#!/usr/bin/env bash
set -euo pipefail
cd /workspace/sportsMLmodel
export SPORTSLAB_HOME="${SPORTSLAB_HOME:-/workspace/.sportsml-private}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
SPORTSLAB_PYTHON="${SPORTSLAB_PYTHON:-/workspace/.sportsml-venv/bin/python}"
umask 077
mkdir -p "$SPORTSLAB_HOME"
# Both processes must be restarted in a new cloud task; live PIDs are not snapshots.
"$SPORTSLAB_PYTHON" -m scripts.refresh --watch >> "$SPORTSLAB_HOME/refresh.log" 2>&1 &
SPORTSLAB_REFRESH_PID=$!
"$SPORTSLAB_PYTHON" -m sportslab.server --host "${SPORTSLAB_BIND:-127.0.0.1}" --port "${PORT:-8765}" &
SPORTSLAB_SERVER_PID=$!
trap 'kill "$SPORTSLAB_REFRESH_PID" "$SPORTSLAB_SERVER_PID" 2>/dev/null || true' EXIT INT TERM
wait -n "$SPORTSLAB_REFRESH_PID" "$SPORTSLAB_SERVER_PID"
