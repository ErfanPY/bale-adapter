#!/usr/bin/env python3
"""
scripts/scan_history.py — one-shot backfill scan for the Bale userbot.

Reads the last N chats (dialogs) from the PlayTalk company Bale account, then
for each PRIVATE chat (1-on-1) grabs recent messages and dumps them to stdout
so you can see what the userbot will be observing going forward.

This is READ-ONLY — it never writes to the KB, never sends anything, never
persists raw text. It just prints what's there.

Usage (on VPS console):
    venv/bin/python scripts/scan_history.py
    venv/bin/python scripts/scan_history.py --limit 10 --history 20 --private-only
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from bale_platform.config import BaleUserbotConfig

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiobale import Client, Dispatcher  # type: ignore
from aiobale.enums import ChatType
from aiobale.types.peer import Peer


def _content_text(content) -> str:
    if content is None:
        return ""
    v = getattr(content, "value", None)
    if isinstance(v, str):
        return v
    cap = getattr(content, "caption", None)
    if cap is not None and isinstance(getattr(cap, "content", None), str):
        return cap.content
    return ""


def _ts(ms: int) -> str:
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ms)


async def main() -> int:
    cfg = BaleUserbotConfig.from_env()
    if not cfg.session_path.exists():
        print("[err] no session file — run scripts/login.py first", file=sys.stderr)
        return 2

    dp = Dispatcher()
    client = Client(dispatcher=dp, session_file=str(cfg.session_path))

    await client.start(run_in_background=True)

    try:
        dialogs = await client.load_dialogs(limit=args.limit)
        print(f"# Loaded {len(dialogs)} dialogs\n")

        private_peers = []
        for d in dialogs:
            peer: Peer = d.peer
            if getattr(peer, "type", None) == 1:  # PeerType.USER
                private_peers.append(d)

        if args.private_only:
            print(f"# Filtering to {len(private_peers)} private chats\n")
            targets = private_peers
        else:
            targets = dialogs

        for d in targets:
            peer = d.peer
            print(f"=== chat peer_id={peer.id} type={peer.type} unread={d.unread_count} ===")
            try:
                msgs = await client.load_history(
                    chat_id=peer.id,
                    chat_type=ChatType.PRIVATE if args.private_only else ChatType(peer.type),
                    limit=args.history,
                )
            except Exception as e:
                print(f"  [err loading history: {e!r}]")
                continue
            for m in reversed(msgs):  # oldest -> newest
                sender = getattr(m, "sender_id", "?")
                txt = _content_text(getattr(m, "content", None))
                print(f"  [{_ts(getattr(m, 'date', 0))}] from={sender}: {txt[:200]}")
            print()

        return 0
    finally:
        await client.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="number of dialogs to scan")
    parser.add_argument("--history", type=int, default=20, help="messages per chat")
    parser.add_argument("--private-only", action="store_true", help="only scan 1-on-1 chats")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main()))
