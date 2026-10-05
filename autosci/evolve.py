"""Variant archive and the gate a proposed self-modification must pass.

This is the interface for improving the framework itself. A change to any part of
it is recorded as a *variant*: the files it touches (with hashes), its parent, and
the benchmark results measured on it. Entries are hash-chained in
state/archive.jsonl.

What the gate checks, mechanically:

* the self-test baseline is clean and every deliberate corruption is caught;
* the calibration card still verifies at level 2 or better;
* the unit tests pass;
* the self-test score is not lower than the parent variant's.

What it does not decide: whether the change is wise, and whether it touched the
frozen core. Changes to the frozen core are listed in `tier0_changed`; they pass
the gate only in the sense that the numbers are fine, and they still need the
maintainer to approve them by merging. `adopt` records that decision after the
merge; it is not a substitute for it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from . import card as cardlib
from . import guard, ledger, runner, selftest
from .canon import digest, sha256_file
from .paths import Layout

CALIBRATION_CARD = "auction-calibration"


class EvolveError(Exception):
    pass


def _variants(layout: Layout) -> list[dict]:
    return [e for e in ledger.read(layout, layout.archive) if e.get("type") == "variant"]


def _adopted(layout: Layout) -> set[str]:
    return {e["id"] for e in ledger.read(layout, layout.archive) if e.get("type") == "adoption"}


def _run_unit_tests(layout: Layout) -> dict:
    tests = layout.root / "tests"
    if not tests.exists():
        return {"ran": False, "passed": False, "detail": "no tests directory"}
    try:
        out = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=str(layout.root),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.SubprocessError as exc:
        return {"ran": True, "passed": False, "detail": f"test run failed: {exc}"}
    tail = (out.stderr or out.stdout).strip().splitlines()[-1:] or [""]
    return {"ran": True, "passed": out.returncode == 0, "detail": tail[0]}


def benchmark(layout: Layout, run_tests: bool = True) -> dict:
    st = selftest.run_selftest(layout.root, CALIBRATION_CARD)
    if cardlib.check_lock(layout, CALIBRATION_CARD) == [f"card {CALIBRATION_CARD} is not locked"]:
        cal = {"level": 0, "problems": ["calibration card missing or not locked"]}
    else:
        v = runner.verify_card(layout, CALIBRATION_CARD)
        cal = {"level": v["level"], "problems": v["problems"]}
    return {
        "selftest": {
            "caught": st["caught"],
            "total": st["total"],
            "missed": st["missed"],
            "baseline_clean": st["baseline_clean"],
            "baseline_problems": st["baseline_problems"],
        },
        "calibration": cal,
        "tests": _run_unit_tests(layout) if run_tests else {"ran": False, "passed": True, "detail": "skipped"},
    }


def gate(layout: Layout, bench: dict, parent: dict | None) -> dict:
    reasons = []
    st = bench["selftest"]
    if not st["baseline_clean"]:
        reasons.append("self-test baseline is not clean: " + "; ".join(st["baseline_problems"][:3]))
    if st["missed"]:
        reasons.append("self-test missed: " + "; ".join(st["missed"]))
    if bench["calibration"]["level"] < 2:
        reasons.append("calibration card does not verify at level 2 or better")
    if not bench["tests"]["passed"]:
        reasons.append("unit tests failed: " + bench["tests"]["detail"])
    if parent is not None:
        pst = parent["benchmark"]["selftest"]
        if pst["total"] and st["total"] and st["caught"] / st["total"] < pst["caught"] / pst["total"]:
            reasons.append("self-test score is lower than the parent's")
    return {"passes": not reasons, "reasons": reasons}


def propose(
    layout: Layout,
    components: list[str],
    parent: str | None,
    note: str,
    base_ref: str | None = None,
    run_tests: bool = True,
) -> dict:
    if not components:
        raise EvolveError("name at least one component file")
    hashes = {}
    for c in components:
        p = layout.root / c
        if not p.is_file():
            raise EvolveError(f"component not found: {c}")
        hashes[Path(c).as_posix()] = sha256_file(p)
    variants = _variants(layout)
    parent_entry = None
    if parent:
        matches = [v for v in variants if v["id"] == parent]
        if not matches:
            raise EvolveError(f"unknown parent variant: {parent}")
        parent_entry = matches[0]
    vid = digest({"components": hashes, "parent": parent})[:12]
    if any(v["id"] == vid for v in variants):
        raise EvolveError(f"variant {vid} is already recorded")
    bench = benchmark(layout, run_tests=run_tests)
    g = gate(layout, bench, parent_entry)
    tier0 = guard.check_against_base(layout, base_ref) if base_ref else guard.check_working_tree(layout)
    return ledger.append(
        layout,
        {
            "type": "variant",
            "id": vid,
            "parent": parent,
            "components": hashes,
            "note": note,
            "benchmark": bench,
            "gate": g,
            "tier0_changed": tier0,
        },
        layout.archive,
    )


def adopt(layout: Layout, variant_id: str, by: str) -> dict:
    matches = [v for v in _variants(layout) if v["id"] == variant_id]
    if not matches:
        raise EvolveError(f"unknown variant: {variant_id}")
    if not matches[0]["gate"]["passes"]:
        raise EvolveError("variant did not pass the gate: " + "; ".join(matches[0]["gate"]["reasons"]))
    if variant_id in _adopted(layout):
        raise EvolveError("variant already adopted")
    return ledger.append(layout, {"type": "adoption", "id": variant_id, "by": by}, layout.archive)


def lineage(layout: Layout) -> list[str]:
    variants = _variants(layout)
    adopted = _adopted(layout)
    children: dict[str | None, list[dict]] = {}
    for v in variants:
        children.setdefault(v["parent"], []).append(v)
    lines: list[str] = []

    def walk(parent_id, depth):
        for v in children.get(parent_id, []):
            st = v["benchmark"]["selftest"]
            flags = [
                "gate pass" if v["gate"]["passes"] else "gate FAIL",
                f"selftest {st['caught']}/{st['total']}",
                "ADOPTED" if v["id"] in adopted else "proposed",
            ]
            if v["tier0_changed"]:
                flags.append(f"frozen core touched ({len(v['tier0_changed'])})")
            lines.append(f"{'  ' * depth}{v['id']}  [{', '.join(flags)}]  {v['note']}")
            walk(v["id"], depth + 1)

    walk(None, 0)
    return lines
