#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/environment.sh"
umask 077
mkdir -p "$SPORTSLAB_HOME"
export SPORTSLAB_DEV_PREVIEW="${SPORTSLAB_DEV_PREVIEW:-1}"
SPORTSLAB_PIDFILE="$SPORTSLAB_HOME/preview.pid"
exec 9>"$SPORTSLAB_HOME/preview.lock"
flock -x 9
preview_running() {
  "$SPORTSLAB_PYTHON" - <<'PY'
import os, urllib.error, urllib.request
base='http://127.0.0.1:'+os.environ.get('PORT','8765')
try:
 with urllib.request.urlopen(base,timeout=1) as r:
  if b'COURTSIDE' not in r.read(): raise ValueError('Unexpected service')
 try: urllib.request.urlopen(base+'/api/state',timeout=1)
 except urllib.error.HTTPError as e:
  if e.code==401: raise SystemExit(0)
except Exception: pass
raise SystemExit(1)
PY
}
stop_preview() {
  if [[ -f "$SPORTSLAB_PIDFILE" ]]; then
    SPORTSLAB_SAVED_PID="$(cat "$SPORTSLAB_PIDFILE")"
    # Only signal this checkout's supervisor, never an arbitrary process reusing its PID.
    if [[ "$SPORTSLAB_SAVED_PID" =~ ^[0-9]+$ ]] && [[ -r "/proc/$SPORTSLAB_SAVED_PID/cmdline" ]]; then
      if grep -zFq "$SPORTSLAB_PROJECT_ROOT/scripts/start.sh" "/proc/$SPORTSLAB_SAVED_PID/cmdline"; then
        kill -TERM "$SPORTSLAB_SAVED_PID" 2>/dev/null || true
        for _ in {1..30}; do
          if ! preview_running; then break; fi
          sleep 0.2
        done
      fi
    fi
    rm -f "$SPORTSLAB_PIDFILE"
  fi
}
case "${1:-start}" in
  stop) stop_preview; echo 'Managed preview stopped.'; exit 0;;
  restart) stop_preview;;
  status) if preview_running; then echo 'Private dashboard responds; sign-in required.'; exit 0; else echo 'Preview is not running.'; exit 1; fi;;
  start) ;;
  *) echo 'Usage: bash scripts/preview.sh [start|status|restart|stop]' >&2; exit 2;;
esac
if preview_running; then
  echo 'Reusing the running private dashboard.'
  exit 0
fi
if [[ ! -x "$SPORTSLAB_PYTHON" ]]; then
  echo 'Run bash scripts/install.sh first.' >&2
  exit 1
fi
nohup bash "$SPORTSLAB_PROJECT_ROOT/scripts/start.sh" >> "$SPORTSLAB_HOME/server.log" 2>&1 < /dev/null 9>&- &
echo "$!" > "$SPORTSLAB_PIDFILE"
for _ in {1..60}; do
  if preview_running; then
    echo "Private preview ready on port ${PORT:-8765}. Password file: $SPORTSLAB_HOME/initial-password.txt"
    exit 0
  fi
  sleep 0.5
done
echo "Preview startup failed; inspect $SPORTSLAB_HOME/server.log" >&2
exit 1
