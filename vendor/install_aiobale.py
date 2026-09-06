#!/usr/bin/env python3
"""vendor/install_aiobale.py — install aiobale from the bundled source zip.

PyPI aiobale is an empty shell. Enalite/aiobale GitHub is gone. Mirrors
ship a zip with no setup.py. We extract the zip, normalize the backslash
paths, and `pip install` the resulting tree as a vendored package.

Run:  python vendor/install_aiobale.py /path/to/venv/bin/pip
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def main() -> int:
    pip = sys.argv[1] if len(sys.argv) > 1 else "pip"
    here = Path(__file__).parent.resolve()
    zip_path = here / "aiobale-source.zip"
    extract_dir = here / "_extracted"

    if not zip_path.exists():
        print(f"vendor: {zip_path} missing", file=sys.stderr)
        return 1

    # Clean and extract
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"[vendor] extracting {zip_path} -> {extract_dir}")
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            # The zip uses backslashes — normalize.
            clean = name.replace("\\", "/")
            target = extract_dir / clean
            if name.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "wb") as f:
                    f.write(z.read(name))

    # Find dist-info dir (aiobale-0.1.5.dist-info lives next to aiobale/).
    dist_info_candidates = list(extract_dir.glob("aiobale-*.dist-info"))
    if not dist_info_candidates:
        # The zip had no dist-info — fall back to creating one by hand.
        print("[vendor] no aiobale-*.dist-info in zip; building minimal dist-info")
        dist_info = extract_dir / "aiobale-0.1.5.dist-info"
        dist_info.mkdir(parents=True, exist_ok=True)
        (dist_info / "METADATA").write_text(
            "Metadata-Version: 2.1\n"
            "Name: aiobale\n"
            "Version: 0.1.5\n"
            "Summary: Async Bale messenger client (vendored from mehrad1232/Aiobale)\n"
        )

    print(f"[vendor] installing {extract_dir} via {pip}")
    result = subprocess.run(
        [pip, "install", "--no-deps", "--quiet", str(extract_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[vendor] pip install failed:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
        return result.returncode

    # Verify import
    verify = subprocess.run(
        [str(Path(pip).parent / "python"), "-c",
         "import aiobale; from aiobale import Client, Dispatcher; print('aiobale OK:', Client.__module__)"],
        capture_output=True,
        text=True,
    )
    print(verify.stdout)
    if verify.returncode != 0:
        print(verify.stderr, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
