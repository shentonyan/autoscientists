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
# What the evidence file holds. "primary-text" is the source's own words;
# "tool-summary" is a summary produced by a fetch tool or a delegate, which is
# weaker: it can omit or distort. The kind is recorded so that readers can weigh it.
EVIDENCE_KINDS = ("primary-text", "tool-summary")


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
    evidence_kind: str | None = None,
) -> dict:
    if status not in STATUSES:
        raise SourceError(f"status must be one of {STATUSES}")
    if evidence_kind is not None and evidence_kind not in EVIDENCE_KINDS:
        raise SourceError(f"evidence kind must be one of {EVIDENCE_KINDS}")
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
        if evidence_kind is None:
            raise SourceError(
                f"a verified source must say what the evidence file holds: one of {EVIDENCE_KINDS}"
            )
        record["evidence_sha256"] = sha256_file(Path(evidence_file))
        record["evidence_kind"] = evidence_kind
    layout.state.mkdir(parents=True, exist_ok=True)
    with open(layout.sources, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return record


def check_evidence(layout: Layout) -> list[str]:
    """Where an evidence file is stored at state/evidence/<id>.txt, its hash must match the record."""
    problems = []
    for s in read(layout):
        if s["status"] != "verified":
            continue
        path = layout.state / "evidence" / f"{s['id']}.txt"
        if path.exists() and sha256_file(path) != s.get("evidence_sha256"):
            problems.append(f"evidence file for source {s['id']} does not match its recorded hash")
    return problems


def cite(layout: Layout, source_id: str) -> dict:
    """Return the record for a citable source, or raise."""
    for s in read(layout):
        if s["id"] == source_id:
            if s["status"] != "verified":
                raise SourceError(f"source {source_id} is {s['status']} and cannot be cited")
            return s
    raise SourceError(f"unknown source: {source_id}")
