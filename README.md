# bale-adapter

Bale userbot adapter (Shape C) for **PlayTalk**'s company Bale account — runs
as a systemd service on the same VPS as `nexa-backend`. It observes every
incoming message in the company account, extracts structured facts into a
knowledge base, and **never** persists raw message text.

This is a SKELETON — no Bale credentials are stored in this repo. The session
file is created interactively on the VPS console by `scripts/login.py`.

## Architecture

```
VPS (130.185.76.124)
└── /opt/bale-adapter/
    ├── .session/session.bale         # aiobale session (opaque protobuf, 0600)
    ├── venv/                          # Python venv with aiobale
    ├── bale_platform/                 # adapter code
    │   ├── adapter.py                 # BaleUserbotAdapter — observe+extract
    │   ├── config.py                  # BaleUserbotConfig
    │   └── runner.py                  # systemd entry point
    ├── kb/learn.py                    # observe-extract (PII-aware)
    ├── systemd/bale-platform.service  # systemd unit
    ├── scripts/bootstrap.sh           # venv + aiobale install (idempotent)
    ├── scripts/login.py               # one-time interactive login
    └── .env                           # BALE_SESSION_PATH, BALE_OBSERVE_ONLY, ...
```

## Why aiobale, not the Bale Bot API

PlayTalk needs the userbot to read **all** customer messages in their company
account, including ones not addressed to a bot. The official `dev.bale.ai`
Bot API only sees messages where the bot is added/mentioned. `aiobale`
(reverse-engineered, GitHub-only — PyPI version is an empty shell) lets us
log into the company account as that user.

> ⚠️ aiobale is unofficial. Excessive POST gRPC calls may trigger Bale rate
> limits. This adapter is **observe-only** by default; we never auto-reply
> in v1.

## Deploy

```bash
git push origin master
# → GitHub Actions: install deps, run tests, ssh into VPS, git pull + restart
```

If the service exits with `No Bale session at ...`, the session file is
missing. Run `scripts/login.py` on the VPS console — the OTP is typed into
that terminal and never leaves the VPS:

```bash
ssh root@130.185.76.124
cd /opt/bale-adapter
source venv/bin/activate
python scripts/login.py
# → enter phone → Bale sends OTP → enter OTP → session written
systemctl restart bale-platform.service
```

## Security

- Session file is `0700` dir + `0600` file
- OTP is read via `getpass`, never logged, never sent to Hermes
- The userbot observes all chats the company account is part of — PlayTalk
  consented to this; the userbot is intended for a corporate account, not
  personal use
- Raw message text is **never** written to disk. Only structured facts land
  in `kb/learned_facts.mdl` (PII-filtered)

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q tests
```

Tests use `tests/_aiobale_stub.py` to avoid pulling in aiobale on CI.
