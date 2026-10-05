"""Governor: when the loop must stop and ask a human.

Absorbed from loops that bound themselves by rounds, convergence and stalls.
Limits live in state/governor.json (protected; the loop may not change them):

    max_trailing_inconclusive   stop after this many most-recent cards in which
                                every hypothesis was inconclusive
    max_dry_cards               stop after this many most-recent cards with no
                                supported hypothesis
    max_lineage_depth           a card that supersedes others may sit at most
                                this deep in a chain of revisions

`decide` reads the ledger; it never changes anything.
"""
from __future__ import annotations

import json

from . import card as cardlib
from . import ledger
from .paths import Layout

DEFAULTS = {"max_trailing_inconclusive": 3, "max_dry_cards": 5, "max_lineage_depth": 3}


def load_config(layout: Layout) -> dict:
    cfg = dict(DEFAULTS)
    if layout.governor_config.exists():
        cfg.update(json.loads(layout.governor_config.read_text(encoding="utf-8")))
    return cfg


def _outcomes(layout: Layout) -> list[tuple[str, list[str]]]:
    """(card id, verdicts of its latest run), ordered by the ledger position of that run."""
    latest: dict[str, dict] = {}
    for e in ledger.read(layout):
        if e.get("type") == "run":
            latest[e["card_id"]] = e
    ordered = sorted(latest.values(), key=lambda e: e["seq"])
    out = []
    for e in ordered:
        rf = layout.run_path(e["run_id"])
        if not rf.exists():
            continue
        ev = json.loads(rf.read_text(encoding="utf-8"))["evaluation"]
        out.append((e["card_id"], [v["verdict"] for v in ev.values()]))
    return out


def lineage_depth(layout: Layout, card_id: str) -> int:
    """Number of earlier cards this one supersedes, following the chain."""
    depth, seen, cur = 0, {card_id}, card_id
    while True:
        try:
            card = cardlib.load_card(layout, cur)
        except cardlib.CardError:
            return depth
        nxt = card.get("supersedes")
        if not nxt or nxt in seen:
            return depth
        depth += 1
        seen.add(nxt)
        cur = nxt


def decide(layout: Layout, card_id: str | None = None) -> dict:
    cfg = load_config(layout)
    outcomes = _outcomes(layout)
    trailing_inc = 0
    for _, verdicts in reversed(outcomes):
        if verdicts and all(v == "inconclusive" for v in verdicts):
            trailing_inc += 1
        else:
            break
    dry = 0
    for _, verdicts in reversed(outcomes):
        if "supported" not in verdicts:
            dry += 1
        else:
            break
    reasons = []
    if trailing_inc >= cfg["max_trailing_inconclusive"]:
        reasons.append(
            f"the last {trailing_inc} cards were entirely inconclusive; "
            "ask the maintainer to look at the question before starting another"
        )
    if dry >= cfg["max_dry_cards"]:
        reasons.append(
            f"the last {dry} cards produced no supported hypothesis; stop and report"
        )
    depth = None
    if card_id:
        depth = lineage_depth(layout, card_id)
        if depth > cfg["max_lineage_depth"]:
            reasons.append(
                f"card {card_id} is revision depth {depth} (limit {cfg['max_lineage_depth']}); "
                "a repeatedly revised design needs a human decision"
            )
    return {
        "stop": bool(reasons),
        "reasons": reasons,
        "stats": {
            "cards_with_runs": len(outcomes),
            "trailing_inconclusive": trailing_inc,
            "dry_cards": dry,
            "lineage_depth": depth,
        },
        "limits": cfg,
    }
