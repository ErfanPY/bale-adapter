#!/usr/bin/env python3
"""
kb/learn.py — observe-extract pattern for the Bale team group.

When the Bale bot receives a message, this module is called to decide:
    1. Does this message add a *new fact* to our PlayTalk knowledge?
    2. If yes → append a structured line to learned_facts.mdl
    3. If no → do nothing (we never store raw messages)

OBSERVE-EXTRACT RULE:
    raw_message_text → NEVER written to disk
    extracted_fact   → written to kb/learned_facts.mdl as one structured line

Run standalone to test:
    python kb/learn.py "my child is 9 years old, can I enroll them?"
    python kb/learn.py "what are the prerequisites for level 3?"
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HERE = Path(__file__).parent.resolve()
FACTS_FILE = HERE / "learned_facts.mdl"
FACTS_FILE.parent.mkdir(parents=True, exist_ok=True)

# Regex patterns for known PlayTalk fact types.
# Order matters: most specific first.
PATTERNS = [
    # (pattern, category, template) — group(1) captures the value
    (r"(?:price|cost|fee|قیمت)[:\s]+(\S+)", "pricing", "pricing: {value}"),
    (r"(?:age|سن)[:\s]+(\d+)\s*(?:year|سال)?", "student_age", "student_age: {value}"),
    (r"level\s*(\d+|one|two|three|four|five|[۱-۵]+)", "course_level", "course_level: {value}"),
    (r"(?:prerequisite|پیش.*نیاز)[:\s]+(.+)", "prerequisite", "prerequisite: {value}"),
    (r"(?:contact|email|ایمیل)[:\s]+(\S+@\S+)", "contact", "contact: {value}"),
    (r"@(\w+)", "social_handle", "social_handle: @{value}"),
    (r"(?:phone|شماره|موبایل)[:\s]+(\+?[\d\s\-]{8,})", "phone", "phone: {value}"),
    (r"(?:schedule|schedule|زمان|ساعت)[:\s]+(.+)", "schedule", "schedule: {value}"),
    (r"(?:Minecraft)[:\s]+(.+)", "platform_detail", "Minecraft_detail: {value}"),
    (r"(?:teacher|instructor|مدرس)[:\s]+(.+)", "teacher", "teacher: {value}"),
    (r"(?:session|جلسه)[:\s]+(\d+)", "session_count", "session_count: {value}"),
]

# What we NEVER store (PII / privacy)
PII_PATTERNS = [
    r"\b\d{10,}\b",          # long digit sequences (national IDs)
    r"\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b",  # card numbers
]


def is_pii(text: str) -> bool:
    """True if the text looks like it contains PII we should not store."""
    for pat in PII_PATTERNS:
        if re.search(pat, text):
            return True
    return False


def normalize_persian_nums(s: str) -> str:
    """Convert Persian/Arabic numerals to ASCII for consistent storage."""
    persian = "۰۱۲۳۴۵۶۷۸۹"
    ascii_map = str.maketrans(persian, "0123456789")
    return s.translate(ascii_map)


def extract_fact(raw_message: str, sender: str = "unknown") -> Optional[str]:
    """Return a structured fact line, or None if nothing worth storing."""
    text = raw_message.strip()

    if is_pii(text):
        return None  # never store PII

    text = normalize_persian_nums(text)

    facts: List[str] = []
    for pattern, category, _template in PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            value = m.group(1).strip().rstrip(".,!?;:")
            facts.append(f"  [{category}] {value}")

    if not facts:
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    lines = [
        f"## Extracted {timestamp} | sender={sender}",
        *facts,
        "",
    ]
    return "\n".join(lines)


def append_fact(fact_line: str) -> None:
    """Append a fact to the learned_facts log."""
    with FACTS_FILE.open("a", encoding="utf-8") as f:
        f.write(fact_line + "\n")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python kb/learn.py <message_text>")
        print("       echo 'msg' | python kb/learn.py")
        sys.exit(1)

    if sys.argv[1] == "-":
        import sys
        text = sys.stdin.read().strip()
    else:
        text = " ".join(sys.argv[1:])

    fact = extract_fact(text)
    if fact:
        append_fact(fact)
        print(f"[stored]\n{fact}")
    else:
        print("[no extractable fact]")


if __name__ == "__main__":
    main()

from typing import List
