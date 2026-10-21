#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/environment.sh"
export SPORTSLAB_DEV_PREVIEW=1
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  export SPORTSLAB_SECURE_COOKIE=1
  export SPORTSLAB_PUBLIC_ORIGIN="https://${CODESPACE_NAME}-${PORT:-8765}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
fi
bash scripts/preview.sh "${1:-start}"
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  # Codespaces defaults to private forwarding; explicitly retain that visibility.
  if ! gh codespace ports visibility "${PORT:-8765}:private" --codespace "$CODESPACE_NAME"; then
    echo 'Could not confirm port visibility. Check Ports → Visibility → Private before use.' >&2
    exit 1
  fi
  echo 'GitHub-authenticated port forwarding is private; the app also requires its own password.'
fi
