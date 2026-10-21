#!/usr/bin/env bash
# Shared portable paths; preserve the existing cloud snapshot defaults.
SPORTSLAB_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPORTSLAB_WORKSPACE_ROOT="$(dirname "$SPORTSLAB_PROJECT_ROOT")"
export SPORTSLAB_HOME="${SPORTSLAB_HOME:-$SPORTSLAB_WORKSPACE_ROOT/.sportsml-private}"
export SPORTSLAB_VENV="${SPORTSLAB_VENV:-$SPORTSLAB_WORKSPACE_ROOT/.sportsml-venv}"
export SPORTSLAB_PYTHON="${SPORTSLAB_PYTHON:-$SPORTSLAB_VENV/bin/python}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
cd "$SPORTSLAB_PROJECT_ROOT"
