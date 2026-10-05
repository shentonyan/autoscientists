"""Report generation.

Every number and verdict in a report is rendered by code from a recorded run.
Free prose is allowed only in a separate notes file, which is included under a
heading that says it is not covered by verification. `verify` regenerates the
report and compares it byte for byte, so a hand-edited report is detected.
"""
from __future__ import annotations

from . import card as cardlib
from .canon import sha256_text
from .paths import Layout
from .runner import LEVELS, verify_card


def _fmt(x) -> str:
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.6g}"
    return str(x)


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render(layout: Layout, card_id: str, verification: dict) -> str:
    card = cardlib.load_card(layout, card_id)
    run = verification["run"]
    entry = verification["entry"]
    level = verification["level"]
    lines: list[str] = []
    add = lines.append

    add(f"# {card['title']}")
    add("")
    add(f"Card `{card_id}` · run `{run['run_id']}` · evidence level **L{level}**: {LEVELS[level]}")
    if verification["problems"]:
        add("")
        add("**Verification problems at generation time:**")
        for p in verification["problems"]:
            add(f"- {p}")
    add("")
    add("## Question")
    add("")
    add(card["question"])
    add("")
    add("## Hypotheses (preregistered)")
    add("")
    add("| id | statement | falsifier | predicted | obtained | match |")
    add("|---|---|---|---|---|---|")
    for h in card["hypotheses"]:
        got = run["evaluation"][h["id"]]["verdict"]
        pred = h.get("predicted_verdict", "")
        match = "" if not pred else ("yes" if pred == got else "NO")
        add(
            f"| {h['id']} | {_cell(h['statement'])} | {_cell(h['falsifier'])} | "
            f"{pred} | **{got}** | {match} |"
        )
    add("")
    add("### Evaluation detail")
    for h in card["hypotheses"]:
        detail = run["evaluation"][h["id"]].get("detail", {})
        add("")
        add(f"**{h['id']}**")
        add("")
        for k in sorted(detail):
            add(f"- {k}: {_fmt(detail[k])}")
    add("")
    add("## Independent cross-checks")
    add("")
    add("| check | observed | reference | tolerance | ok |")
    add("|---|---|---|---|---|")
    for c in run["crosscheck"]:
        add(
            f"| {_cell(c['name'])} | {_fmt(c['observed'])} | {_fmt(c['reference'])} | "
            f"{_fmt(c['tolerance'])} | {_fmt(c['ok'])} |"
        )
    add("")
    add("## Provenance")
    add("")
    add(f"- seeds: {', '.join(str(s) for s in run['seeds'])}")
    add(f"- card sha256: `{run['card_sha256']}`")
    add(f"- experiment sha256: `{run['experiment_sha256']}`")
    add(f"- results sha256: `{entry['results_sha256']}`")
    add(f"- ledger entry: seq {entry['seq']}, `{entry['entry_sha256']}`")
    if card.get("sources"):
        add(f"- cited sources (all recorded as verified): {', '.join(card['sources'])}")
    add("")
    add("## Interpretation (author prose, not covered by verification)")
    add("")
    notes_path = layout.notes_path(card_id)
    if notes_path.exists():
        notes = notes_path.read_text(encoding="utf-8").rstrip("\n")
        add(notes)
        add("")
        add(f"_notes sha256: `{sha256_text(notes)}`_")
    else:
        add("_none written_")
    add("")
    return "\n".join(lines)


def write_report(layout: Layout, card_id: str) -> tuple[str, dict]:
    verification = verify_card(layout, card_id)
    if verification["run"] is None:
        raise cardlib.CardError("no run to report on; run the card first")
    text = render(layout, card_id, verification)
    layout.reports.mkdir(parents=True, exist_ok=True)
    layout.report_path(card_id).write_text(text, encoding="utf-8")
    return text, verification


def check_report_current(layout: Layout, card_id: str, verification: dict) -> list[str]:
    path = layout.report_path(card_id)
    if not path.exists():
        return []
    if verification["run"] is None:
        return ["report exists but no run is recorded"]
    expected = render(layout, card_id, verification)
    if path.read_text(encoding="utf-8") != expected:
        return ["report differs from the one generated from the ledger (edited by hand or stale)"]
    return []
