#!/usr/bin/env python3
"""
kb/scrape_playtalk.py — scrape PlayTalk public data into the KB.

Run locally (playtalk.ir is unreachable from this VM but reachable from VPS):

    python kb/scrape_playtalk.py

Or via hermes chat:

    hermes chat -q "run python kb/scrape_playtalk.py and summarize what was found"

Sources:
    1. playtalk.ir  — main site (landing, pricing, about)
    2. ble.ir/playtalk — Bale channel preview (description, pinned post)

Output (appended to kb/playtalk_seed.mdl):

    ## PlayTalk Knowledge Seed
    scraped: YYYY-MM-DD
    source: <url>

    ### Courses / Programs
    - ...

    ### Pricing
    - ...

    ### Contact
    - ...

    ### Tone of voice
    - ...
"""

from __future__ import annotations

import json
import logging
import os
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    import httpx
except ImportError:
    print("httpx required: pip install httpx")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
log = logging.getLogger("scrape_playtalk")

HERE = Path(__file__).parent
OUT_FILE = HERE / "playtalk_seed.mdl"
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

SOURCES = [
    ("playtalk.ir", "https://playtalk.ir"),
    ("ble_channel", "https://ble.ir/playtalk"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; HermesAgent/1.0; +https://github.com/NousResearch/hermes-agent) "
        "PlayTalk-KB-Scraper/1.0"
    ),
    "Accept-Language": "fa,en;q=0.9",
}


def _build_md(source: str, url: str, sections: List[Dict[str, Any]]) -> str:
    """Render one source's content as a markdown section."""
    lines = [
        f"### Source: {source}",
        f"URL: {url}",
        "",
    ]
    for sec in sections:
        title = sec.get("title", "General")
        content = sec.get("content", "").strip()
        if not content:
            continue
        lines.append(f"#### {title}")
        for para in content.split("\n"):
            para = para.strip()
            if not para:
                continue
            # wrap at 80 cols for readability
            wrapped = textwrap.fill(para, width=80, break_long_words=False)
            lines.append(wrapped)
        lines.append("")
    return "\n".join(lines)


def scrape_ble_channel() -> List[Dict[str, Any]]:
    """Read ble.ir/playtalk — channel preview / description."""
    sections: List[Dict[str, Any]] = []
    try:
        resp = httpx.get("https://ble.ir/playtalk", headers=HEADERS, timeout=15.0)
        resp.raise_for_status()
        text = resp.text
    except Exception as exc:
        log.warning("ble.ir/playtalk unreachable: %s", exc)
        return sections

    # The channel preview page has structured metadata — extract what we can.
    # Channel name, description, member count, pinned post text.
    import re

    # Member count
    m = re.search(r"(\d[\d,]*) عضو", text)
    member_count = m.group(1).replace(",", "") if m else "unknown"

    # Description lines
    desc_lines: List[str] = []
    # Look for the main tagline block (Farsi text near the top)
    for line in text.split("\n"):
        line = line.strip()
        if 20 < len(line) < 300 and not line.startswith("<") and not line.startswith("{"):
            desc_lines.append(line)

    description = " ".join(desc_lines[:10])  # first 10 meaningful lines

    sections.append(
        {
            "title": "Channel Info",
            "content": f"Member count: {member_count}\nHandle: @playtalk\nAdmin contact: @playtalk_admin",
        }
    )
    if description:
        sections.append({"title": "Channel Description", "content": description})

    return sections


def scrape_main_site() -> List[Dict[str, Any]]:
    """Try to scrape playtalk.ir for courses, pricing, contact."""
    sections: List[Dict[str, Any]] = []
    try:
        resp = httpx.get("https://playtalk.ir", headers=HEADERS, timeout=15.0)
        resp.raise_for_status()
        text = resp.text
    except Exception as exc:
        log.warning("playtalk.ir unreachable: %s — this VM likely has no route to it", exc)
        return sections

    import re

    # Strip HTML tags for a rough text extraction
    clean = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"&\w+?;", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Extract visible paragraphs (lines between 40-500 chars)
    lines = [l.strip() for l in clean.split(".") if 40 < len(l.strip()) < 500]
    unique_lines = list(dict.fromkeys(lines))[:50]  # dedup, cap 50

    sections.append({"title": "Site Content (top 50 paragraphs)", "content": ".\n".join(unique_lines)})
    return sections


def main() -> None:
    all_content: List[str] = [
        f"## PlayTalk Knowledge Seed",
        f"scraped: {TODAY}",
        "",
    ]

    for source_name, url in SOURCES:
        log.info("scraping %s (%s)", source_name, url)
        if source_name == "ble_channel":
            sections = scrape_ble_channel()
        else:
            sections = scrape_main_site()

        if not sections:
            log.info("  — no content retrieved")
            continue

        md = _build_md(source_name, url, sections)
        all_content.append(md)
        log.info("  — %d sections written", len(sections))

    if len(all_content) <= 4:
        log.warning(
            "Nothing scraped — playtalk.ir is likely unreachable from this machine. "
            "Run this script on the VPS (130.185.76.124) where it has direct internet access."
        )
        sys.exit(0)

    output = "\n".join(all_content) + "\n"
    OUT_FILE.write_text(output, encoding="utf-8")
    log.info("KB seed written → %s  (%d bytes)", OUT_FILE, len(output))


if __name__ == "__main__":
    main()
