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
from aiobale.types.peer import PeerType
from aiobale.types.peer import Peer


def _content_text(content) -> str:
    if content is None:
        return ""
    t = getattr(content, "text", None)
    if t is not None and isinstance(getattr(t, "value", None), str):
        return t.value
    v = getattr(content, "value", None)
    if isinstance(v, str):
        return v
    doc = getattr(content, "document", None)
    if doc is not None:
        cap = getattr(doc, "caption", None)
        if cap is not None and isinstance(getattr(cap, "content", None), str):
            return f"[file] {cap.content}"
        return "[file]"
    return "[empty/other]"


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
            if PeerType(getattr(peer, "type", 0)) == PeerType.PRIVATE:  # 1-on-1 chat
                private_peers.append(d)
        if args.private_only:
            print(f"# Filtering to {len(private_peers)} private chats\n")
            targets = private_peers
        else:
            targets = dialogs

        name_map: dict[int, str] = {}
        if args.get_names:
            # Resolve display names for private peers (local_name when set, else profile name)
            for d in targets:
                pid = d.peer.id
                try:
                    u = await client.load_user(chat_id=pid, chat_type=ChatType.PRIVATE)
                    name_map[pid] = getattr(u, "local_name", None) or getattr(u, "name", "") or str(pid)
                except Exception:
                    name_map[pid] = str(pid)
            print("# Names: " + ", ".join(f"{pid}={nm}" for pid, nm in name_map.items()) + "\n")

        for d in targets:
            peer = d.peer
            label = name_map.get(peer.id, str(peer.id))
            print(f"=== chat {label} (id={peer.id}) unread={d.unread_count} ===")
            try:
                msgs = await client.load_history(
                    chat_id=peer.id,
                    chat_type=ChatType.PRIVATE if args.private_only else ChatType(peer.type),
                    limit=args.history,
                )
                if not isinstance(msgs, list):  # 0.1.5 returned HistoryResponse; 0.3.8 returns list
                    msgs = msgs.data
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
    parser.add_argument("--no-names", action="store_true", help="skip resolving contact names (faster)")
    args = parser.parse_args()
    args.get_names = not args.no_names
    raise SystemExit(asyncio.run(main()))
