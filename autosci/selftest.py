"""Self-test: can the verifier catch deliberate tampering?

This is the benchmark a proposed change to the verifier must not regress. It
copies the repository's data (cards, experiments, runs, reports, state) into a
temporary directory, checks that the calibration card verifies cleanly, then
applies one deliberate corruption at a time and requires that at least one check
notices. The score is mutations caught out of mutations tried.

It measures the checks the framework claims to make. It does not measure the
checks it does not claim, and it cannot see a failure of design. The known blind
spots are listed in BLIND_SPOTS and printed with every result so a high score is
not mistaken for a safe system.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from . import ledger, report, runner, sources
from . import card as cardlib
from .paths import Layout

DATA_DIRS = ("cards", "experiments", "runs", "reports", "state")

BLIND_SPOTS = [
    "a cross-check that is weak or not really independent, if it is weak before the card is locked",
    "a decision rule in the experiment that is biased before the card is locked",
    "an evidence file that is a wrong or invented summary: its hash proves identity, not truth",
    "notes that draw an unsupported conclusion from numbers that are themselves supported",
    "numbers written out in words in the notes",
    "someone who rewrites the lock, the ledger and the git history together",
    "a question that is the wrong one to ask",
]


def detect(layout: Layout, card_id: str) -> list[str]:
    """Run every check the framework has and return all problems found."""
    problems = ledger.verify_chain(layout)
    v = runner.verify_card(layout, card_id)
    problems += v["problems"]
    problems += report.check_report_current(layout, card_id, v)
    problems += report.check_notes(layout, card_id, v)
    problems += sources.check_evidence(layout)
    return problems


def _first_number(run: dict):
    for hid in sorted(run["evaluation"]):
        detail = run["evaluation"][hid].get("detail", {})
        for key in sorted(detail):
            val = detail[key]
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return val
    return None


def _mutate_first_number(obj) -> bool:
    """Change the first numeric leaf found, in place. Return whether one was changed."""
    if isinstance(obj, dict):
        for k in sorted(obj):
            v = obj[k]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                obj[k] = v + 1
                return True
            if _mutate_first_number(v):
                return True
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                obj[i] = v + 1
                return True
            if _mutate_first_number(v):
                return True
    return False


def _latest_run_file(layout: Layout, card_id: str) -> Path:
    return layout.run_path(ledger.runs_for_card(layout, card_id)[-1]["run_id"])


def _mut_card_seeds(layout, card_id, ctx):
    p = layout.card_path(card_id)
    card = json.loads(p.read_text(encoding="utf-8"))
    card["seeds"] = card["seeds"] + [987654]
    p.write_text(json.dumps(card), encoding="utf-8")


def _mut_experiment(layout, card_id, ctx):
    card = cardlib.load_card(layout, card_id)
    p = layout.experiment_path(card["experiment"])
    p.write_text(p.read_text(encoding="utf-8") + "\n# edited after lock\n", encoding="utf-8")


def _mut_lock_deleted(layout, card_id, ctx):
    layout.lock_path(card_id).unlink()


def _mut_run_result(layout, card_id, ctx):
    rf = _latest_run_file(layout, card_id)
    data = json.loads(rf.read_text(encoding="utf-8"))
    if not _mutate_first_number(data["results"]):
        raise RuntimeError("no numeric result to edit")
    rf.write_text(json.dumps(data), encoding="utf-8")


def _mut_run_deleted(layout, card_id, ctx):
    _latest_run_file(layout, card_id).unlink()


def _mut_ledger_edit(layout, card_id, ctx):
    lines = layout.ledger.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    entry["results_sha256"] = "0" * 64
    lines[0] = json.dumps(entry, sort_keys=True)
    layout.ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mut_ledger_forged(layout, card_id, ctx):
    entries = ledger.read(layout)
    forged = {
        "seq": len(entries),
        "prev": entries[-1]["entry_sha256"],
        "type": "run",
        "card_id": card_id,
        "run_id": "forged",
        "results_sha256": "0" * 64,
        "entry_sha256": "0" * 64,
    }
    with open(layout.ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(forged, sort_keys=True) + "\n")


def _mut_report_edit(layout, card_id, ctx):
    p = layout.report_path(card_id)
    p.write_text("Edited by hand.\n\n" + p.read_text(encoding="utf-8"), encoding="utf-8")


def _append_note(layout, card_id, line, regenerate=True):
    p = layout.notes_path(card_id)
    p.write_text(p.read_text(encoding="utf-8").rstrip("\n") + "\n" + line + "\n", encoding="utf-8")
    if regenerate:
        # Regenerate the report so that a stale report is not what catches the edit;
        # the notes lint has to catch it on its own.
        report.write_report(layout, card_id)


def _mut_notes_fabricated(layout, card_id, ctx):
    _append_note(layout, card_id, f"The effect was {ctx['fake_number']} in every run.")


def _mut_notes_unlisted_source(layout, card_id, ctx):
    _append_note(layout, card_id, "[context] Another project reports the same. [src:not-in-this-card]")


def _mut_notes_context_unsourced(layout, card_id, ctx):
    _append_note(layout, card_id, "[context] This is well established in the literature.")


def _mut_notes_stale(layout, card_id, ctx):
    _append_note(
        layout, card_id, "[conjecture] A harmless extra line added after the report was generated.",
        regenerate=False,
    )


def _mut_evidence(layout, card_id, ctx):
    files = sorted((layout.state / "evidence").glob("*.txt")) if (layout.state / "evidence").exists() else []
    if not files:
        raise LookupError("no evidence files to tamper with")
    files[0].write_text(files[0].read_text(encoding="utf-8") + "\nforged line\n", encoding="utf-8")


# (description, function, text that must appear in at least one reported problem)
MUTATIONS: list[tuple[str, Callable, str]] = [
    ("card seeds edited after lock", _mut_card_seeds, "card changed after lock"),
    ("experiment source edited after lock", _mut_experiment, "experiment source changed"),
    ("lock file deleted", _mut_lock_deleted, "is not locked"),
    ("a recorded result edited", _mut_run_result, "do not match the ledger"),
    ("run file deleted", _mut_run_deleted, "run file missing"),
    ("ledger entry edited", _mut_ledger_edit, "does not match its hash"),
    ("forged ledger entry appended", _mut_ledger_forged, "does not match its hash"),
    ("report edited by hand", _mut_report_edit, "report differs"),
    ("notes: fabricated number", _mut_notes_fabricated, "does not appear in the recorded results"),
    ("notes: source not listed in the card", _mut_notes_unlisted_source, "not listed in the card"),
    ("notes: context claim without a source", _mut_notes_context_unsourced, "needs a [src:ID] tag"),
    ("notes edited after the report was generated", _mut_notes_stale, "report differs"),
    ("evidence file tampered", _mut_evidence, "evidence file"),
]


def run_selftest(root: Path | str, card_id: str = "auction-calibration") -> dict:
    src = Layout(root)
    result = {
        "baseline_clean": False,
        "baseline_problems": [],
        "caught": 0,
        "total": 0,
        "missed": [],
        "skipped": [],
        "blind_spots": BLIND_SPOTS,
    }
    with tempfile.TemporaryDirectory() as tmp:
        base_root = Path(tmp) / "base"
        base_root.mkdir()
        for d in DATA_DIRS:
            if (src.root / d).exists():
                shutil.copytree(src.root / d, base_root / d)
        base = Layout(base_root)

        # Baseline: a valid notes file grounded in a recorded number, report regenerated.
        v0 = runner.verify_card(base, card_id)
        if v0["run"] is None:
            result["baseline_problems"] = v0["problems"] or ["no recorded run"]
            return result
        number = _first_number(v0["run"])
        if number is None:
            result["baseline_problems"] = ["the calibration run has no numeric evaluation detail to cite"]
            return result
        base.reports.mkdir(exist_ok=True)
        base.notes_path(card_id).write_text(
            f"The first recorded evaluation value was {report._fmt(number)}.\n", encoding="utf-8"
        )
        report.write_report(base, card_id)
        problems = detect(base, card_id)
        result["baseline_problems"] = problems
        result["baseline_clean"] = not problems
        if problems:
            return result

        fake = round(float(number) * 7.31 + 13.17, 5)
        ctx = {"fake_number": fake}
        for i, (name, fn, expect) in enumerate(MUTATIONS):
            work_root = Path(tmp) / f"m{i}"
            shutil.copytree(base_root, work_root)
            work = Layout(work_root)
            try:
                fn(work, card_id, ctx)
            except LookupError:
                result["skipped"].append(name)
                continue
            result["total"] += 1
            found = detect(work, card_id)
            if any(expect in p for p in found):
                result["caught"] += 1
            elif found:
                result["missed"].append(f"{name} (flagged, but not by the check meant to catch it)")
            else:
                result["missed"].append(name)
    return result
