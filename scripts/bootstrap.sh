#!/usr/bin/env bash
# bale-adapter bootstrap — idempotent.
# Runs as ExecStartPre= before the bale-platform runner starts.
#
# Responsibilities:
#   1. Ensure /opt/bale-adapter/.session/ exists with mode 0700.
#   2. Ensure Python venv at /opt/bale-adapter/venv.
#   3. Install aiobale (from GitHub; PyPI version is an empty shell), httpx, pyyaml.
#   4. Ensure kb/ + logs/ directories exist.
#   5. Make scripts/login.py executable.
#
# NEVER touches Bale credentials — those are entered by the operator via
# scripts/login.py on the VPS console.

set -euo pipefail
cd /opt/bale-adapter

SESSION_DIR="/opt/bale-adapter/.session"
mkdir -p "$SESSION_DIR"
chmod 0700 "$SESSION_DIR"

mkdir -p /opt/bale-adapter/kb /opt/bale-adapter/logs

VENV="/opt/bale-adapter/venv"
if [ ! -d "$VENV" ]; then
    echo "[bootstrap] creating venv at $VENV"
    python3 -m venv "$VENV"
fi

# install deps (idempotent; pip is fast on cached wheels)
"$VENV/bin/pip" install --quiet --upgrade pip >/dev/null

# aiobale: install from GitHub (mehrad1232/Aiobale is the freshest mirror after
# Enalite/aiobale was taken down). PyPI aiobale is an empty package, do not use.
"$VENV/bin/pip" install --quiet "git+https://github.com/mehrad1232/Aiobale.git" >/dev/null
"$VENV/bin/pip" install --quiet pydantic aiohttp aiofiles httpx pyyaml >/dev/null

chmod +x /opt/bale-adapter/scripts/login.py

echo "[bootstrap] ok — venv=$VENV aiobale installed; session dir = $SESSION_DIR"
