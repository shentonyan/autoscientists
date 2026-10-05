"""Source registry.

The framework cannot decide whether a source says what a write-up claims. What
it can do is refuse to let a report cite anything that has not been recorded as
read, with a hash of the evidence text that was actually read. The reading
itself (fetching the page, checking the passage) is done by the agent or the
maintainer and recorded here; `unverified` entries can be listed as leads but
never cited.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .canon import sha256_file
from .paths import Layout

STATUSES = ("verified", "unverified")


class SourceError(Exception):
    pass


def read(layout: Layout) -> list[dict]:
    if not layout.sources.exists():
        return []
    with open(layout.sources, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def add(
    layout: Layout,
    source_id: str,
    url: str,
    title: str,
    status: str,
    evidence_file: Path | None = None,
    supports: str = "",
) -> dict:
    if status not in STATUSES:
        raise SourceError(f"status must be one of {STATUSES}")
    if any(s["id"] == source_id for s in read(layout)):
        raise SourceError(f"source id already exists: {source_id}")
    record = {
        "id": source_id,
        "url": url,
        "title": title,
        "status": status,
        "supports": supports,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if status == "verified":
        if evidence_file is None or not Path(evidence_file).exists():
            raise SourceError("a verified source needs --evidence-file: the text that was actually read")
        record["evidence_sha256"] = sha256_file(Path(evidence_file))
    layout.state.mkdir(parents=True, exist_ok=True)
    with open(layout.sources, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return record


def cite(layout: Layout, source_id: str) -> dict:
    """Return the record for a citable source, or raise."""
    for s in read(layout):
        if s["id"] == source_id:
            if s["status"] != "verified":
                raise SourceError(f"source {source_id} is {s['status']} and cannot be cited")
            return s
    raise SourceError(f"unknown source: {source_id}")
