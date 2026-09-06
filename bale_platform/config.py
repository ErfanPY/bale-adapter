"""Config for the Bale userbot adapter.

All paths and behavior knobs fall back to env vars / defaults.

IMPORTANT: aiobale's Client.__init__ forces the session file path to end in
`.bale` via `path.with_suffix(".bale")`. We default to `session.bale` so the
suffix is preserved. The session file contains opaque protobuf bytes that
aiobale writes itself during validate_code() — there is no JWT string to
manually persist.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


# NOTE: filename MUST end in .bale — aiobale's Client.__init__ does
# `path.with_suffix(".bale")` and resolves the new path. If you pass
# `/opt/bale-adapter/.session/jwt` it becomes `/opt/bale-adapter/.session/jwt.bale`.
# We default to `session.bale` for clarity and to avoid surprise.
SESSION_PATH = Path(os.getenv("BALE_SESSION_PATH", "/opt/bale-adapter/.session/session.bale"))
KB_DIR = Path(os.getenv("BALE_KB_DIR", "/opt/bale-adapter/kb"))
LOG_FILE = Path(os.getenv("BALE_LOG_FILE", "/opt/bale-adapter/logs/userbot.log"))


@dataclass
class BaleUserbotConfig:
    """Runtime config for the Bale userbot.

    All fields fall back to env vars, mirroring the Telegram adapter pattern.
    """

    session_path: Path = SESSION_PATH
    kb_dir: Path = KB_DIR
    log_file: Path = LOG_FILE
    allowed_chats: Optional[List[str]] = None
    observe_only: bool = True  # default: NEVER auto-send replies
    reconnect_min_seconds: float = 2.0
    reconnect_max_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "BaleUserbotConfig":
        def _csv(name: str) -> List[str]:
            v = os.getenv(name, "")
            return [s.strip() for s in v.split(",") if s.strip()]

        def _bool(name: str, default: bool) -> bool:
            v = os.getenv(name, "")
            if not v:
                return default
            return v.strip().lower() in {"1", "true", "yes", "on"}

        return cls(
            session_path=Path(os.getenv("BALE_SESSION_PATH", str(SESSION_PATH))),
            kb_dir=Path(os.getenv("BALE_KB_DIR", str(KB_DIR))),
            log_file=Path(os.getenv("BALE_LOG_FILE", str(LOG_FILE))),
            allowed_chats=_csv("BALE_ALLOWED_CHATS") or None,
            observe_only=_bool("BALE_OBSERVE_ONLY", True),
        )


def is_configured() -> bool:
    """Pre-flight: aiobale's session file (opaque protobuf bytes) must exist."""
    return SESSION_PATH.exists() and SESSION_PATH.stat().st_size > 0
