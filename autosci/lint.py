"""Lint for the notes file: every number and every cited source must be grounded.

The notes file is the only place prose is allowed. This check catches the most
mechanical kinds of fabrication in it:

* a number that appears nowhere in the recorded results, the card, or counts
  derived from them;
* a `[src:ID]` tag pointing at a source that is not recorded as verified, or that
  the card does not list;
* a `[context]` line (background that did not come from this run) with no source.

Tags a line may carry:

    [conjecture]   the line says what the author thinks; numbers are exempt
    [context]      background from outside this run; requires a [src:ID] tag
    [src:ID]       cites a source recorded with `source-add`

The lint is an aid, not a proof. Prose that restates a supported number but draws
an unsupported conclusion from it passes, and so does a number written out in
words. Review still has to read the notes.
"""
from __future__ import annotations

import json
import re

from . import sources
from .paths import Layout

NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE]-?\d+)?(?!\w)")
SRC = re.compile(r"\[src:([A-Za-z0-9_.-]+)\]")
LIST_PREFIX = re.compile(r"^\s*(?:[-*]\s+)?\d+[.)]\s+")
PLACEHOLDERS = ("DATA_NEEDED", "CITATION NEEDED")


def numbers_in(text: str) -> list[float]:
    out = []
    for m in NUM.finditer(text):
        try:
            out.append(float(m.group(0)))
        except ValueError:
            pass
    return out


def reference_numbers(report_body: str, card: dict) -> list[float]:
    ref = numbers_in(report_body) + numbers_in(json.dumps(card, ensure_ascii=False))
    ref += [float(len(card.get("seeds", []))), float(len(card.get("hypotheses", [])))]
    return ref


def _decimals(token: str) -> int:
    base = re.split(r"[eE]", token)[0]
    return len(base.split(".")[1]) if "." in base else 0


def _supported(token: str, reference: list[float]) -> bool:
    value = float(token)
    d = _decimals(token)
    for r in reference:
        if abs(r - value) < 1e-12:
            return True
        if d > 0 and abs(round(r, d) - value) < 1e-12:
            return True
        if d == 0 and abs(round(r) - value) < 1e-12 and "e" not in token.lower():
            return True
    return False


def lint_notes(layout: Layout, notes: str, report_body: str, card: dict) -> dict:
    """Return {"problems": [...], "open": [...]}."""
    problems: list[str] = []
    open_items: list[str] = []
    reference = reference_numbers(report_body, card)
    card_sources = set(card.get("sources", []))
    for lineno, raw in enumerate(notes.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        for ph in PLACEHOLDERS:
            if ph in line:
                open_items.append(f"line {lineno}: unresolved placeholder {ph}")
        cited = SRC.findall(line)
        for sid in cited:
            if sid not in card_sources:
                problems.append(f"line {lineno}: source '{sid}' is not listed in the card's sources")
                continue
            try:
                sources.cite(layout, sid)
            except sources.SourceError as exc:
                problems.append(f"line {lineno}: {exc}")
        if "[context]" in line and not cited:
            problems.append(f"line {lineno}: a [context] line needs a [src:ID] tag")
        if "[conjecture]" in line or "[context]" in line:
            continue
        scan = SRC.sub(" ", line)
        scan = LIST_PREFIX.sub("", scan)
        for m in NUM.finditer(scan):
            if not _supported(m.group(0), reference):
                problems.append(
                    f"line {lineno}: number {m.group(0)} does not appear in the recorded results or card"
                )
    return {"problems": problems, "open": open_items}
