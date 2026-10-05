"""Research cards: the pre-registration unit.

A card fixes, before any run, the question, the hypotheses with their
falsifiers, the experiment module, its parameters and the seeds. `lock` records
the hash of the card and of the experiment source. After locking, any edit to
either file is detected by `check_lock`.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .canon import digest, sha256_file
from .paths import Layout

VERDICTS = ("supported", "refuted", "inconclusive")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


class CardError(Exception):
    pass


def load_card(layout: Layout, card_id: str) -> dict:
    path = layout.card_path(card_id)
    if not path.exists():
        raise CardError(f"card not found: {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate(card: dict) -> list[str]:
    """Return a list of problems; empty means the card is well formed."""
    problems: list[str] = []
    for key in ("id", "title", "question", "experiment", "params", "seeds", "hypotheses"):
        if key not in card:
            problems.append(f"missing field: {key}")
    if problems:
        return problems
    if not isinstance(card["id"], str) or not ID_RE.match(card["id"]):
        problems.append("id must match [a-z0-9][a-z0-9_-]{1,63}")
    if not isinstance(card["params"], dict):
        problems.append("params must be an object")
    seeds = card["seeds"]
    if not (isinstance(seeds, list) and seeds and all(isinstance(s, int) for s in seeds)):
        problems.append("seeds must be a non-empty list of integers")
    elif len(set(seeds)) != len(seeds):
        problems.append("seeds must be distinct")
    hyps = card["hypotheses"]
    if not (isinstance(hyps, list) and hyps):
        problems.append("hypotheses must be a non-empty list")
        return problems
    sup = card.get("supersedes")
    if sup is not None and not (isinstance(sup, str) and ID_RE.match(sup)):
        problems.append("supersedes must be a card id")
    deps = card.get("depends_on", [])
    if not isinstance(deps, list):
        problems.append("depends_on must be a list")
    else:
        for i, d in enumerate(deps):
            where = f"depends_on[{i}]"
            if not (isinstance(d, dict) and set(d) == {"card", "hypothesis", "verdict"}):
                problems.append(f"{where} must have exactly: card, hypothesis, verdict")
            elif d["verdict"] not in VERDICTS:
                problems.append(f"{where}.verdict must be one of {VERDICTS}")
    seen = set()
    for i, h in enumerate(hyps):
        where = f"hypotheses[{i}]"
        if not isinstance(h, dict):
            problems.append(f"{where} must be an object")
            continue
        for key in ("id", "statement", "falsifier"):
            if not str(h.get(key, "")).strip():
                problems.append(f"{where}.{key} is required and non-empty")
        hid = h.get("id")
        if hid in seen:
            problems.append(f"{where}.id duplicated: {hid}")
        seen.add(hid)
        pv = h.get("predicted_verdict")
        if pv is not None and pv not in VERDICTS:
            problems.append(f"{where}.predicted_verdict must be one of {VERDICTS}")
    return problems


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def current_hashes(layout: Layout, card: dict) -> dict:
    exp_path = layout.experiment_path(card["experiment"])
    if not exp_path.exists():
        raise CardError(f"experiment module not found: {exp_path}")
    return {"card_sha256": digest(card), "experiment_sha256": sha256_file(exp_path)}


def lock(layout: Layout, card_id: str) -> dict:
    card = load_card(layout, card_id)
    problems = validate(card)
    if problems:
        raise CardError("card invalid: " + "; ".join(problems))
    hashes = current_hashes(layout, card)
    lock_path = layout.lock_path(card_id)
    if lock_path.exists():
        existing = json.loads(lock_path.read_text(encoding="utf-8"))
        if (existing["card_sha256"], existing["experiment_sha256"]) == (
            hashes["card_sha256"],
            hashes["experiment_sha256"],
        ):
            return existing
        raise CardError(
            "card already locked with different content; a locked card is immutable. "
            "Create a new card id for a revised design."
        )
    record = {"card_id": card_id, **hashes, "locked_at": _utcnow()}
    lock_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def check_lock(layout: Layout, card_id: str) -> list[str]:
    """Return problems found between the lock file and the files on disk."""
    lock_path = layout.lock_path(card_id)
    if not lock_path.exists():
        return [f"card {card_id} is not locked"]
    try:
        card = load_card(layout, card_id)
        hashes = current_hashes(layout, card)
    except CardError as exc:
        return [str(exc)]
    rec = json.loads(lock_path.read_text(encoding="utf-8"))
    problems = []
    if rec["card_sha256"] != hashes["card_sha256"]:
        problems.append("card changed after lock")
    if rec["experiment_sha256"] != hashes["experiment_sha256"]:
        problems.append("experiment source changed after lock")
    return problems
