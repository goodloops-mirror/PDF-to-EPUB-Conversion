#!/usr/bin/env bash
# Launcher: manages the in-repo venv and runs project commands. Nothing is written outside this repo.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PIP_CACHE_DIR="$ROOT/.cache/pip"
export PYTHONPYCACHEPREFIX="$ROOT/.cache/pycache"
export PIP_DISABLE_PIP_VERSION_CHECK=1
VENV="$ROOT/.venv"
if [ ! -x "$VENV/bin/python" ]; then python3 -m venv "$VENV"; fi
if [ ! -f "$VENV/.installed" ] || [ "$ROOT/requirements.txt" -nt "$VENV/.installed" ]; then
  "$VENV/bin/pip" install -q -r "$ROOT/requirements.txt" && touch "$VENV/.installed"
fi
set -a; [ -f "$ROOT/.env" ] && . "$ROOT/.env"; set +a
exec "$VENV/bin/python" -I "$@"
