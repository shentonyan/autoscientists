"""Running locked cards and verifying the result.

An experiment is a Python file in experiments/ that exposes:

    run(params, seed) -> dict          one seeded execution, JSON-serialisable
    evaluate(params, per_seed) -> dict hypothesis id -> {"verdict": ..., "detail": {...}}
    crosscheck(params, per_seed) -> list of
        {"name", "observed", "reference", "tolerance", "ok"}

`crosscheck` must compute its reference by a route that does not share code
with `run` (a closed form, exact enumeration, a published value that is
recorded as a verified source). That independence is what gives a check its
value.
"""
from __future__ import annotations

import importlib.util
import json
import platform
from pathlib import Path

from . import card as cardlib
from . import ledger, sources
from .canon import digest
from .paths import Layout

LEVELS = {
    0: "unverified: at least one check failed or is missing",
    1: "reproducible: a fresh re-execution gives byte-identical results",
    2: "cross-checked: level 1, and every independent cross-check passed",
    3: "sourced: level 2, and every cited source is recorded as verified",
}


class RunError(Exception):
    pass


def load_experiment(layout: Layout, name: str):
    path = layout.experiment_path(name)
    spec = importlib.util.spec_from_file_location(f"autosci_experiment_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for fn in ("run", "evaluate", "crosscheck"):
        if not hasattr(module, fn):
            raise RunError(f"experiment {name} lacks required function: {fn}")
    return module


def _jsonable(obj):
    """Round-trip through JSON so stored and fresh results compare equal."""
    return json.loads(json.dumps(obj, sort_keys=True))


def execute(layout: Layout, card: dict) -> dict:
    module = load_experiment(layout, card["experiment"])
    params = card["params"]
    per_seed = {str(seed): _jsonable(module.run(params, seed)) for seed in card["seeds"]}
    evaluation = _jsonable(module.evaluate(params, per_seed))
    checks = _jsonable(module.crosscheck(params, per_seed))
    declared = {h["id"] for h in card["hypotheses"]}
    if set(evaluation) != declared:
        raise RunError(
            f"evaluate() must return a verdict for exactly the preregistered hypotheses "
            f"{sorted(declared)}, got {sorted(evaluation)}"
        )
    for hid, ev in evaluation.items():
        if ev.get("verdict") not in cardlib.VERDICTS:
            raise RunError(f"hypothesis {hid}: verdict must be one of {cardlib.VERDICTS}")
    return {"results": per_seed, "evaluation": evaluation, "crosscheck": checks}


def run_card(layout: Layout, card_id: str) -> dict:
    problems = cardlib.check_lock(layout, card_id)
    if problems:
        raise RunError("refusing to run: " + "; ".join(problems))
    card = cardlib.load_card(layout, card_id)
    hashes = cardlib.current_hashes(layout, card)
    out = execute(layout, card)
    results_sha = digest(out["results"])
    run_id = digest({**hashes, "results_sha256": results_sha})[:16]
    record = {
        "run_id": run_id,
        "card_id": card_id,
        **hashes,
        "seeds": card["seeds"],
        **out,
    }
    layout.runs.mkdir(parents=True, exist_ok=True)
    layout.run_path(run_id).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not any(e.get("run_id") == run_id for e in ledger.runs_for_card(layout, card_id)):
        ledger.append(
            layout,
            {
                "type": "run",
                "run_id": run_id,
                "card_id": card_id,
                **hashes,
                "results_sha256": results_sha,
                "python": platform.python_version(),
            },
        )
    return record


def verify_card(layout: Layout, card_id: str) -> dict:
    """Independent re-check. Returns {"problems": [...], "level": int, "run": record|None}."""
    problems: list[str] = []
    problems += ledger.verify_chain(layout)
    problems += cardlib.check_lock(layout, card_id)
    entries = ledger.runs_for_card(layout, card_id)
    if not entries:
        problems.append("no recorded run for this card")
        return {"problems": problems, "level": 0, "run": None, "entry": None}
    latest = entries[-1]
    run_file = layout.run_path(latest["run_id"])
    stored = None
    if not run_file.exists():
        problems.append(f"run file missing: {run_file.name}")
    else:
        stored = json.loads(run_file.read_text(encoding="utf-8"))
        if digest(stored["results"]) != latest["results_sha256"]:
            problems.append("stored results do not match the ledger hash")

    reproducible = False
    checks_ok = False
    if not cardlib.check_lock(layout, card_id):
        card = cardlib.load_card(layout, card_id)
        fresh = execute(layout, card)
        reproducible = digest(fresh["results"]) == latest["results_sha256"]
        if not reproducible:
            problems.append(
                "fresh re-execution differs from the recorded results "
                "(check the Python version recorded in the ledger)"
            )
        if stored is not None and fresh["evaluation"] != stored["evaluation"]:
            problems.append("stored evaluation differs from a fresh evaluation")
        checks = fresh["crosscheck"]
        failed = [c["name"] for c in checks if not c.get("ok")]
        if not checks:
            problems.append("experiment declares no independent cross-check")
        elif failed:
            problems.append("cross-check failed: " + ", ".join(failed))
        checks_ok = bool(checks) and not failed

        source_ids = card.get("sources", [])
        sourced = False
        if source_ids:
            try:
                for sid in source_ids:
                    sources.cite(layout, sid)
                sourced = True
            except sources.SourceError as exc:
                problems.append(f"source problem: {exc}")
    else:
        sourced = False

    level = 0
    if not problems:
        level = 1
        if checks_ok:
            level = 2
            if sourced:
                level = 3
    return {"problems": problems, "level": level, "run": stored, "entry": latest}
