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

    # Install aiobale by symlinking into the venv's site-packages.
    # We do this because the bundled zip has no setup.py / pyproject.toml,
    # which modern pip refuses to install. The dist-info (if present) is
    # copied alongside so `pip show aiobale` still works.
    import site

    candidate_pythons = []
    pip_path = Path(pip)
    if pip_path.name in ("pip", "pip3") and pip_path.parent.name == "bin":
        candidate_pythons.append(pip_path.parent / "python")
    candidate_pythons.append(Path(sys.executable))

    site_packages = None
    for py in candidate_pythons:
        if not py.exists():
            continue
        r = subprocess.run(
            [str(py), "-c", "import site; print(site.getsitepackages()[0])"],
            capture_output=True, text=True, check=True,
        )
        site_packages = Path(r.stdout.strip())
        break

    if site_packages is None:
        print("[vendor] could not determine site-packages", file=sys.stderr)
        return 2

    src_pkg = extract_dir / "aiobale"
    dst_pkg = site_packages / "aiobale"
    if dst_pkg.exists() or dst_pkg.is_symlink():
        if dst_pkg.is_symlink() or dst_pkg.is_file():
            dst_pkg.unlink()
        else:
            shutil.rmtree(dst_pkg)
    os.symlink(src_pkg, dst_pkg)
    print(f"[vendor] symlinked {src_pkg} -> {dst_pkg}")

    if dist_info_candidates:
        for di in dist_info_candidates:
            shutil.copytree(di, site_packages / di.name, dirs_exist_ok=True)
            print(f"[vendor] copied dist-info {di.name} -> {site_packages}")
    else:
        # No dist-info in the zip — build a minimal one so `pip show` works.
        dist_info = site_packages / "aiobale-0.1.5.dist-info"
        dist_info.mkdir(parents=True, exist_ok=True)
        (dist_info / "METADATA").write_text(
            "Metadata-Version: 2.1\n"
            "Name: aiobale\n"
            "Version: 0.1.5\n"
            "Summary: Async Bale messenger client (vendored from mehrad1232/Aiobale)\n"
        )
        (dist_info / "RECORD").write_text("aiobale/__init__.py,,\n")
        print(f"[vendor] created minimal dist-info {dist_info}")

    # Verify import
    for py in candidate_pythons:
        if not py.exists():
            continue
        verify = subprocess.run(
            [str(py), "-c",
             "import aiobale; from aiobale import Client, Dispatcher; print('aiobale OK:', Client.__module__)"],
            capture_output=True, text=True,
        )
        print(verify.stdout, end="")
        if verify.returncode != 0:
            print(verify.stderr, file=sys.stderr)
            return 1
        break
    return 0


if __name__ == "__main__":
    sys.exit(main())
