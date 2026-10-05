"""Command line: python -m autosci <command>."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import card as cardlib
from . import ledger, report, runner, sources
from .paths import Layout

TEMPLATE = {
    "id": "",
    "title": "",
    "question": "",
    "experiment": "",
    "params": {},
    "seeds": [1, 2, 3],
    "hypotheses": [
        {
            "id": "H1",
            "statement": "",
            "falsifier": "",
            "predicted_verdict": "supported",
        }
    ],
    "sources": [],
}


def _layout(args) -> Layout:
    return Layout(args.root) if args.root else Layout()


def cmd_new(args) -> int:
    layout = _layout(args)
    path = layout.card_path(args.card_id)
    if path.exists():
        print(f"card already exists: {path}", file=sys.stderr)
        return 1
    layout.cards.mkdir(parents=True, exist_ok=True)
    tpl = dict(TEMPLATE, id=args.card_id)
    path.write_text(json.dumps(tpl, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote template {path}")
    return 0


def cmd_validate(args) -> int:
    problems = cardlib.validate(cardlib.load_card(_layout(args), args.card_id))
    for p in problems:
        print(f"- {p}")
    print("card is well formed" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_lock(args) -> int:
    rec = cardlib.lock(_layout(args), args.card_id)
    print(f"locked {args.card_id}: card {rec['card_sha256'][:12]}, experiment {rec['experiment_sha256'][:12]}")
    return 0


def cmd_run(args) -> int:
    rec = runner.run_card(_layout(args), args.card_id)
    print(f"run {rec['run_id']} recorded")
    for hid, ev in rec["evaluation"].items():
        print(f"  {hid}: {ev['verdict']}")
    return 0


def _print_verification(v: dict, extra: list[str]) -> int:
    problems = v["problems"] + extra
    for p in problems:
        print(f"- {p}")
    if problems:
        print(f"VERIFY FAILED ({len(problems)} problem(s))")
        return 1
    print(f"verified: level L{v['level']} ({runner.LEVELS[v['level']]})")
    return 0


def cmd_verify(args) -> int:
    layout = _layout(args)
    v = runner.verify_card(layout, args.card_id)
    extra = report.check_report_current(layout, args.card_id, v)
    return _print_verification(v, extra)


def cmd_report(args) -> int:
    layout = _layout(args)
    _, v = report.write_report(layout, args.card_id)
    print(f"wrote {layout.report_path(args.card_id)}")
    return _print_verification(v, [])


def cmd_cycle(args) -> int:
    layout = _layout(args)
    problems = cardlib.validate(cardlib.load_card(layout, args.card_id))
    if problems:
        for p in problems:
            print(f"- {p}")
        return 1
    cardlib.lock(layout, args.card_id)
    rec = runner.run_card(layout, args.card_id)
    print(f"run {rec['run_id']}")
    _, v = report.write_report(layout, args.card_id)
    extra = report.check_report_current(layout, args.card_id, v)
    return _print_verification(v, extra)


def cmd_status(args) -> int:
    layout = _layout(args)
    chain = ledger.verify_chain(layout)
    print("ledger chain: " + ("ok" if not chain else "BROKEN: " + "; ".join(chain)))
    cards = sorted(p for p in layout.cards.glob("*.json") if not p.name.endswith(".lock.json"))
    if not cards:
        print("no cards")
    for p in cards:
        cid = p.stem
        locked = layout.lock_path(cid).exists()
        runs = ledger.runs_for_card(layout, cid)
        line = f"{cid}: {'locked' if locked else 'draft'}, {len(runs)} run(s)"
        if runs:
            rf = layout.run_path(runs[-1]["run_id"])
            if rf.exists():
                ev = json.loads(rf.read_text(encoding="utf-8"))["evaluation"]
                line += " | " + ", ".join(f"{h}={d['verdict']}" for h, d in ev.items())
        print(line)
    return 0


def cmd_source_add(args) -> int:
    rec = sources.add(
        _layout(args),
        args.source_id,
        args.url,
        args.title,
        args.status,
        Path(args.evidence_file) if args.evidence_file else None,
        args.supports or "",
    )
    print(f"recorded source {rec['id']} ({rec['status']})")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="autosci", description=__doc__)
    ap.add_argument("--root", help="repository root (default: this checkout)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name, fn, helptext in (
        ("new", cmd_new, "write an empty card template"),
        ("validate", cmd_validate, "check a card is well formed"),
        ("lock", cmd_lock, "pre-register: hash card and experiment source"),
        ("run", cmd_run, "execute a locked card and record it in the ledger"),
        ("verify", cmd_verify, "re-execute and check everything independently"),
        ("report", cmd_report, "generate the report from the ledger"),
        ("cycle", cmd_cycle, "validate, lock, run, report, verify"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("card_id")
        p.set_defaults(fn=fn)

    p = sub.add_parser("status", help="list cards and ledger health")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("source-add", help="record a source that was actually read")
    p.add_argument("source_id")
    p.add_argument("--url", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--status", choices=sources.STATUSES, required=True)
    p.add_argument("--evidence-file", help="text that was read; required when status is verified")
    p.add_argument("--supports", help="one line: what the source is cited for")
    p.set_defaults(fn=cmd_source_add)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except (cardlib.CardError, runner.RunError, sources.SourceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
