# vendor/aiobale — local source bundle

## Why a vendored zip

- **PyPI `aiobale` is an empty shell** — `aiobale/__init__.py` is literally one
  line. Don't `pip install aiobale`.
- **`Enalite/aiobale` GitHub repo was taken down** (the original was the
  most-cited Bale client). `pip install git+https://github.com/Enalite/aiobale`
  fails with "Repository not found".
- **Mirrors** like `mehrad1232/Aiobale` republish the source code, but they
  don't ship a `pyproject.toml` or `setup.py` — only a single `aiobale.zip`
  inside the repo. So `pip install git+...` fails with "neither setup.py
  nor pyproject.toml found".

## What we do instead

We bundle the `aiobale.zip` (downloaded from
`https://raw.githubusercontent.com/mehrad1232/Aiobale/main/aiobale.zip`) and
install it directly:

```bash
pip install ./vendor/aiobale-source.zip
```

`install_aiobale.sh` is a fallback that extracts the zip manually and installs
the package directory if the direct `pip install` fails for any reason.

## Updating the zip

If aiobale gets a real public release:

```bash
curl -fsSL -o vendor/aiobale-source.zip \
    https://raw.githubusercontent.com/mehrad1232/Aiobale/main/aiobale.zip
```

Or — better — once aiobale is back on PyPI with a real release, drop this
whole vendor/ directory and switch the bootstrap back to `pip install aiobale`.
