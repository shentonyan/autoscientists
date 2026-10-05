"""Append-only, hash-chained ledger of runs.

Each entry commits to the previous entry's hash, so editing or deleting an old
entry breaks every later link. This detects accidental or after-the-fact edits;
it is not a defence against someone rewriting the whole file and repository
history, which git history review covers.
"""
from __future__ import annotations

import json

from .canon import digest
from .paths import Layout

GENESIS = "0" * 64


def read(layout: Layout) -> list[dict]:
    if not layout.ledger.exists():
        return []
    entries = []
    with open(layout.ledger, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _entry_hash(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "entry_sha256"}
    return digest(body)


def append(layout: Layout, record: dict) -> dict:
    entries = read(layout)
    prev = entries[-1]["entry_sha256"] if entries else GENESIS
    entry = {"seq": len(entries), "prev": prev, **record}
    entry["entry_sha256"] = _entry_hash(entry)
    layout.state.mkdir(parents=True, exist_ok=True)
    with open(layout.ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    return entry


def verify_chain(layout: Layout) -> list[str]:
    problems = []
    prev = GENESIS
    for i, entry in enumerate(read(layout)):
        if entry.get("seq") != i:
            problems.append(f"entry {i}: seq is {entry.get('seq')}")
        if entry.get("prev") != prev:
            problems.append(f"entry {i}: broken link to previous entry")
        if entry.get("entry_sha256") != _entry_hash(entry):
            problems.append(f"entry {i}: content does not match its hash")
        prev = entry.get("entry_sha256", "")
    return problems


def runs_for_card(layout: Layout, card_id: str) -> list[dict]:
    return [e for e in read(layout) if e.get("type") == "run" and e.get("card_id") == card_id]
