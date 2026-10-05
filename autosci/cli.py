"""Command line: python -m autosci <command>."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import card as cardlib
from . import calibration, evolve, governor, guard, ledger, report, runner, selftest, sources
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
    extra += report.check_notes(layout, args.card_id, v, strict=args.strict)
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
    extra += report.check_notes(layout, args.card_id, v)
    return _print_verification(v, extra)


def cmd_status(args) -> int:
    layout = _layout(args)
    chain = ledger.verify_chain(layout)
    print("ledger chain: " + ("ok" if not chain else "BROKEN: " + "; ".join(chain)))
    ev = sources.check_evidence(layout)
    n_src = len(sources.read(layout))
    print(f"sources: {n_src} recorded, evidence hashes " + ("ok" if not ev else "MISMATCH: " + "; ".join(ev)))
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
        args.evidence_kind,
    )
    print(f"recorded source {rec['id']} ({rec['status']})")
    return 0


def cmd_govern(args) -> int:
    d = governor.decide(_layout(args), args.card)
    st = d["stats"]
    print(
        f"cards with runs: {st['cards_with_runs']}, trailing inconclusive: {st['trailing_inconclusive']}, "
        f"dry cards: {st['dry_cards']}, lineage depth: {st['lineage_depth']}"
    )
    for r in d["reasons"]:
        print(f"STOP: {r}")
    if not d["stop"]:
        print("continue")
    return 2 if d["stop"] else 0


def cmd_calibration(args) -> int:
    s = calibration.summarize(_layout(args))
    print(f"predictions counted: {s['n']} (excluded calibration cards: {s['excluded']})")
    if s["n"]:
        print(f"hit rate: {s['hits']}/{s['n']} = {s['rate']:.2f}")
        for pred, d in sorted(s["by_predicted"].items()):
            print(f"  predicted {pred}: {d['hits']}/{d['n']}")
        for m in s["misses"]:
            print(f"  miss: {m['card']}.{m['hypothesis']} predicted {m['predicted']}, got {m['obtained']}")
    if not s["informative"]:
        print(f"fewer than {calibration.MIN_FOR_ANY_CONCLUSION} predictions: too few to say anything about calibration")
    return 0


def cmd_lint(args) -> int:
    layout = _layout(args)
    v = runner.verify_card(layout, args.card_id)
    problems = report.check_notes(layout, args.card_id, v, strict=args.strict)
    for p in problems:
        print(f"- {p}")
    print("notes ok" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_guard(args) -> int:
    layout = _layout(args)
    if args.update:
        m = guard.update(layout)
        print(f"manifest updated: {len(m['files'])} protected files")
        return 0
    problems = (
        guard.check_against_base(layout, args.base) if args.base else guard.check_working_tree(layout)
    )
    for p in problems:
        print(f"- {p}")
    if problems:
        print("FROZEN CORE DIFFERS: the maintainer must approve these changes")
        return 1
    print("frozen core unchanged")
    return 0


def cmd_selftest(args) -> int:
    layout = _layout(args)
    r = selftest.run_selftest(layout.root, args.card_id)
    if not r["baseline_clean"]:
        print("baseline is not clean:")
        for p in r["baseline_problems"]:
            print(f"- {p}")
        return 1
    print(f"caught {r['caught']} of {r['total']} deliberate corruptions")
    for m in r["missed"]:
        print(f"  MISSED: {m}")
    for m in r["skipped"]:
        print(f"  skipped (not applicable here): {m}")
    print("known blind spots, not measured by this score:")
    for b in r["blind_spots"]:
        print(f"  - {b}")
    return 1 if r["missed"] else 0


def cmd_evolve(args) -> int:
    layout = _layout(args)
    if args.evolve_cmd == "propose":
        e = evolve.propose(
            layout, args.component, args.parent, args.note, args.base, run_tests=not args.skip_tests
        )
        g = e["gate"]
        st = e["benchmark"]["selftest"]
        print(f"variant {e['id']} recorded; selftest {st['caught']}/{st['total']}")
        print("gate: " + ("pass" if g["passes"] else "FAIL"))
        for r in g["reasons"]:
            print(f"  - {r}")
        if e["tier0_changed"]:
            print("frozen core touched; maintainer approval needed:")
            for t in e["tier0_changed"]:
                print(f"  - {t}")
        return 0 if g["passes"] else 1
    if args.evolve_cmd == "adopt":
        e = evolve.adopt(layout, args.variant_id, args.by)
        print(f"variant {e['id']} adopted by {e['by']}")
        return 0
    lines = evolve.lineage(layout)
    print("\n".join(lines) if lines else "no variants recorded")
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
        if name == "verify":
            p.add_argument("--strict", action="store_true", help="unresolved placeholders in notes are errors")
        p.set_defaults(fn=fn)

    p = sub.add_parser("status", help="list cards and ledger health")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("source-add", help="record a source that was actually read")
    p.add_argument("source_id")
    p.add_argument("--url", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--status", choices=sources.STATUSES, required=True)
    p.add_argument("--evidence-file", help="text that was read; required when status is verified")
    p.add_argument(
        "--evidence-kind",
        choices=sources.EVIDENCE_KINDS,
        help="what the evidence file holds; required when status is verified",
    )
    p.add_argument("--supports", help="one line: what the source is cited for")
    p.set_defaults(fn=cmd_source_add)

    p = sub.add_parser("govern", help="should the loop stop and ask a human?")
    p.add_argument("--card", help="also check this card's revision depth")
    p.set_defaults(fn=cmd_govern)

    p = sub.add_parser("calibration", help="how often predicted verdicts matched")
    p.set_defaults(fn=cmd_calibration)

    p = sub.add_parser("lint", help="check the notes file against the recorded results")
    p.add_argument("card_id")
    p.add_argument("--strict", action="store_true", help="unresolved placeholders are errors")
    p.set_defaults(fn=cmd_lint)

    p = sub.add_parser("guard", help="check the frozen core against its manifest or a base ref")
    p.add_argument("--base", help="git ref whose manifest the maintainer has approved, e.g. origin/main")
    p.add_argument("--update", action="store_true", help="rewrite the manifest (maintainer)")
    p.set_defaults(fn=cmd_guard)

    p = sub.add_parser("selftest", help="deliberately corrupt a copy and check the verifier notices")
    p.add_argument("card_id", nargs="?", default="auction-calibration")
    p.set_defaults(fn=cmd_selftest)

    p = sub.add_parser("evolve", help="variant archive for changes to the framework itself")
    esub = p.add_subparsers(dest="evolve_cmd", required=True)
    ep = esub.add_parser("propose", help="record a variant and measure it")
    ep.add_argument("--component", action="append", required=True, help="file touched; repeatable")
    ep.add_argument("--parent", help="id of the variant this one improves on")
    ep.add_argument("--note", required=True)
    ep.add_argument("--base", help="git ref with the approved manifest, e.g. origin/main")
    ep.add_argument("--skip-tests", action="store_true")
    ap_ = esub.add_parser("adopt", help="record that the maintainer merged a variant")
    ap_.add_argument("variant_id")
    ap_.add_argument("--by", required=True)
    esub.add_parser("status", help="show the lineage")
    p.set_defaults(fn=cmd_evolve)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except (cardlib.CardError, runner.RunError, sources.SourceError, evolve.EvolveError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
