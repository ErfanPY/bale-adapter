#!/usr/bin/env bash
# vendor/install_aiobale.sh — install aiobale from the bundled source zip.
# We bundle the zip because:
#   1. PyPI's aiobale is an empty shell (aiobale/__init__.py is 0 lines)
#   2. The original Enalite/aiobale GitHub repo was taken down
#   3. Mirrors like mehrad1232/Aiobale have no pyproject.toml — they only
#      host the aiobale/ source tree as a single zip inside the repo
#
# This script extracts the zip and installs it as a regular package via pip.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP="$SCRIPT_DIR/aiobale-source.zip"
DEST="$SCRIPT_DIR/_extracted"
PIP="${1:-pip}"

if [ ! -f "$ZIP" ]; then
    echo "vendor: $ZIP missing" >&2
    exit 1
fi

# Extract; the zip uses backslashes for path separators, so normalize.
rm -rf "$DEST"
mkdir -p "$DEST"
"$PIP" install --quiet "$ZIP" && exit 0

# Fallback: unzip manually and use the extracted dir as PYTHONPATH target.
python3 - <<PYEOF
import zipfile, os, shutil
src = "$ZIP"
dst = "$DEST"
if os.path.exists(dst):
    shutil.rmtree(dst)
os.makedirs(dst, exist_ok=True)
with zipfile.ZipFile(src) as z:
    for name in z.namelist():
        clean = name.replace("\\", "/")
        target = os.path.join(dst, clean)
        if name.endswith("/"):
            os.makedirs(target, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(z.read(name))
print(f"extracted aiobale to {dst}")
PYEOF

# Install the extracted package (its name is in aiobale-*.dist-info).
WHL_DIR=$(ls -d "$DEST"/aiobale-*.dist-info 2>/dev/null | head -1 || true)
if [ -n "$WHL_DIR" ]; then
    SRC_DIR=$(dirname "$WHL_DIR")
    "$PIP" install --quiet "$SRC_DIR"
else
    echo "vendor: no aiobale-*.dist-info found in extracted zip" >&2
    exit 2
fi
