#!/usr/bin/env bash
set -euo pipefail
umask 077
source "$(dirname "${BASH_SOURCE[0]}")/environment.sh"
python3 -m venv "$SPORTSLAB_VENV"
"$SPORTSLAB_PYTHON" -m pip install --disable-pip-version-check -r requirements.txt
# Fetch the archived baseline only on an empty NBA database, preserving existing user data.
"$SPORTSLAB_PYTHON" - <<'PY'
import os, runpy
from sportslab.data import connect
root=os.environ['SPORTSLAB_HOME'];db=connect(root)
empty=db.execute("SELECT COUNT(*) FROM games WHERE league='NBA'").fetchone()[0]==0;db.close()
if empty:runpy.run_module('scripts.import_nba',run_name='__main__')
PY
"$SPORTSLAB_PYTHON" -m scripts.refresh
"$SPORTSLAB_PYTHON" - <<'PYCODE'
import os, subprocess, sys
from sportslab.data import connect
with connect(os.environ['SPORTSLAB_HOME']) as db:
 needs=db.execute("SELECT COUNT(*) FROM games WHERE league='NHL'").fetchone()[0]<700
if needs:
 result=subprocess.run([sys.executable,'-m','scripts.backfill_nhl'])
 if result.returncode:print('NHL backfill incomplete; inspect source/network status. Other setup continues.')
PYCODE
"$SPORTSLAB_PYTHON" -m scripts.seed_models
"$SPORTSLAB_PYTHON" -m scripts.backup "$SPORTSLAB_HOME/backups"
"$SPORTSLAB_PYTHON" -m pytest -q
