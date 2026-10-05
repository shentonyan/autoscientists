"""Calibration of the author's predictions.

Cards may record a predicted verdict per hypothesis before the run. This module
compares predictions with what was obtained. Cards whose id contains
"calibration" are excluded: their predictions are known answers by design and
would flatter the rate.
"""
from __future__ import annotations

import json

from . import card as cardlib
from . import ledger
from .paths import Layout

MIN_FOR_ANY_CONCLUSION = 10


def collect(layout: Layout) -> list[dict]:
    latest: dict[str, dict] = {}
    for e in ledger.read(layout):
        if e.get("type") == "run":
            latest[e["card_id"]] = e
    rows = []
    for card_id, entry in sorted(latest.items(), key=lambda kv: kv[1]["seq"]):
        rf = layout.run_path(entry["run_id"])
        if not rf.exists():
            continue
        try:
            card = cardlib.load_card(layout, card_id)
        except cardlib.CardError:
            continue
        ev = json.loads(rf.read_text(encoding="utf-8"))["evaluation"]
        for h in card["hypotheses"]:
            pred = h.get("predicted_verdict")
            if pred is None or h["id"] not in ev:
                continue
            rows.append(
                {
                    "card": card_id,
                    "hypothesis": h["id"],
                    "predicted": pred,
                    "obtained": ev[h["id"]]["verdict"],
                    "excluded": "calibration" in card_id,
                }
            )
    return rows


def summarize(layout: Layout) -> dict:
    rows = collect(layout)
    counted = [r for r in rows if not r["excluded"]]
    hits = sum(1 for r in counted if r["predicted"] == r["obtained"])
    by_pred: dict[str, dict] = {}
    for r in counted:
        d = by_pred.setdefault(r["predicted"], {"n": 0, "hits": 0})
        d["n"] += 1
        d["hits"] += int(r["predicted"] == r["obtained"])
    n = len(counted)
    return {
        "n": n,
        "hits": hits,
        "rate": (hits / n) if n else None,
        "by_predicted": by_pred,
        "misses": [r for r in counted if r["predicted"] != r["obtained"]],
        "excluded": len(rows) - n,
        "informative": n >= MIN_FOR_ANY_CONCLUSION,
    }
