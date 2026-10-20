#!/usr/bin/env bash
set -euo pipefail
umask 077
cd /workspace/sportsMLmodel
export SPORTSLAB_HOME="${SPORTSLAB_HOME:-/workspace/.sportsml-private}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python -m venv /workspace/.sportsml-venv
/workspace/.sportsml-venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
# Fetch the archived baseline only on an empty NBA database, preserving existing user data.
/workspace/.sportsml-venv/bin/python - <<'PY'
import os, runpy
from sportslab.data import connect
root=os.environ['SPORTSLAB_HOME'];db=connect(root)
empty=db.execute("SELECT COUNT(*) FROM games WHERE league='NBA'").fetchone()[0]==0;db.close()
if empty:runpy.run_module('scripts.import_nba',run_name='__main__')
PY
/workspace/.sportsml-venv/bin/python -m scripts.refresh
/workspace/.sportsml-venv/bin/python -m scripts.seed_models
/workspace/.sportsml-venv/bin/python -m scripts.backup "$SPORTSLAB_HOME/backups"
/workspace/.sportsml-venv/bin/python -m pytest -q
