"""Tests for the mechanisms added in the second iteration: governor, calibration,
dependencies, notes lint, guard, self-test and the variant archive."""
import json
import subprocess
import unittest
from unittest import mock

from test_framework import CARD, EXPERIMENT, Base

from autosci import calibration, evolve, governor, guard, lint, report, runner, selftest, sources
from autosci import card as cardlib


def make_card(base, card_id, verdict="supported", predicted=None, extra=None):
    """Write, lock and run a tiny card whose experiment returns a fixed verdict."""
    exp_name = f"exp_{card_id.replace('-', '_')}"
    code = EXPERIMENT.replace(
        'return {"H1": {"verdict": "supported" if abs(m - 0.5) < 0.05 else "refuted",',
        f'return {{"H1": {{"verdict": "{verdict}",',
    )
    base.layout.experiment_path(exp_name).write_text(code, encoding="utf-8")
    card = json.loads(json.dumps(CARD))
    card.update({"id": card_id, "experiment": exp_name})
    if predicted:
        card["hypotheses"][0]["predicted_verdict"] = predicted
    else:
        card["hypotheses"][0].pop("predicted_verdict", None)
    card.update(extra or {})
    base.layout.card_path(card_id).write_text(json.dumps(card), encoding="utf-8")
    cardlib.lock(base.layout, card_id)
    return runner.run_card(base.layout, card_id)


class TestGovernor(Base):
    def test_stops_after_trailing_inconclusive(self):
        for i in range(3):
            make_card(self, f"inc{i}", "inconclusive")
        d = governor.decide(self.layout)
        self.assertTrue(d["stop"])
        self.assertEqual(d["stats"]["trailing_inconclusive"], 3)

    def test_a_supported_card_resets_the_streak(self):
        make_card(self, "ca", "inconclusive")
        make_card(self, "cb", "inconclusive")
        make_card(self, "cc", "supported")
        self.assertFalse(governor.decide(self.layout)["stop"])

    def test_stops_when_dry(self):
        for i in range(5):
            make_card(self, f"dry{i}", "refuted")
        d = governor.decide(self.layout)
        self.assertTrue(d["stop"])
        self.assertEqual(d["stats"]["dry_cards"], 5)

    def test_revision_depth_limit(self):
        make_card(self, "r0", "supported")
        prev = "r0"
        for i in range(1, 5):
            make_card(self, f"r{i}", "supported", extra={"supersedes": prev})
            prev = f"r{i}"
        self.assertEqual(governor.lineage_depth(self.layout, "r4"), 4)
        self.assertTrue(governor.decide(self.layout, "r4")["stop"])
        self.assertFalse(governor.decide(self.layout, "r2")["stop"])

    def test_limits_can_be_configured(self):
        self.layout.state.mkdir(exist_ok=True)
        self.layout.governor_config.write_text(json.dumps({"max_dry_cards": 1}), encoding="utf-8")
        make_card(self, "cx", "refuted")
        self.assertTrue(governor.decide(self.layout)["stop"])


class TestCalibration(Base):
    def test_hit_rate_counts_only_predictions(self):
        make_card(self, "p1", "supported", predicted="supported")
        make_card(self, "p2", "refuted", predicted="supported")
        make_card(self, "p3", "supported")  # no prediction recorded
        s = calibration.summarize(self.layout)
        self.assertEqual((s["n"], s["hits"]), (2, 1))
        self.assertEqual(s["misses"][0]["card"], "p2")
        self.assertFalse(s["informative"])

    def test_calibration_cards_are_excluded(self):
        make_card(self, "auction-calibration-toy", "supported", predicted="supported")
        s = calibration.summarize(self.layout)
        self.assertEqual((s["n"], s["excluded"]), (0, 1))


class TestDependencies(Base):
    def dep(self, verdict="supported"):
        return {"depends_on": [{"card": "base", "hypothesis": "H1", "verdict": verdict}]}

    def test_run_allowed_when_premise_holds(self):
        make_card(self, "base", "supported")
        make_card(self, "child", "supported", extra=self.dep())

    def test_run_refused_when_premise_was_refuted(self):
        make_card(self, "base", "refuted")
        with self.assertRaises(runner.RunError):
            make_card(self, "child", "supported", extra=self.dep())

    def test_run_refused_when_premise_never_ran(self):
        base_card = json.loads(json.dumps(CARD))
        base_card["id"] = "base"
        self.layout.card_path("base").write_text(json.dumps(base_card), encoding="utf-8")
        cardlib.lock(self.layout, "base")
        with self.assertRaises(runner.RunError):
            make_card(self, "child", "supported", extra=self.dep())

    def test_malformed_dependency_rejected(self):
        bad = dict(CARD, depends_on=[{"card": "base"}])
        self.assertTrue(any("depends_on" in p for p in cardlib.validate(bad)))
        bad = dict(CARD, depends_on=[{"card": "b", "hypothesis": "H1", "verdict": "maybe"}])
        self.assertTrue(any("verdict" in p for p in cardlib.validate(bad)))


class TestLint(Base):
    def setUp(self):
        super().setUp()
        self.cycle()

    def check(self, notes, strict=False):
        self.layout.notes_path("toy").write_text(notes, encoding="utf-8")
        report.write_report(self.layout, "toy")
        v = runner.verify_card(self.layout, "toy")
        return report.check_notes(self.layout, "toy", v, strict=strict)

    def test_grounded_notes_pass(self):
        self.assertEqual(self.check("The pooled mean was about 0.5 over 3 seeds.\n"), [])

    def test_list_numbering_is_ignored(self):
        self.assertEqual(self.check("1. The mean was close to 0.5.\n2. Nothing else.\n"), [])

    def test_fabricated_number_flagged(self):
        problems = self.check("The effect was 42.7 units.\n")
        self.assertTrue(any("42.7" in p for p in problems))

    def test_conjecture_exempts_numbers(self):
        self.assertEqual(self.check("[conjecture] I expect 99 to matter.\n"), [])

    def test_context_without_source_flagged(self):
        self.assertTrue(any("needs a [src:ID]" in p for p in self.check("[context] Well known.\n")))

    def test_source_not_in_card_flagged(self):
        problems = self.check("[context] Another project agrees. [src:nowhere]\n")
        self.assertTrue(any("not listed in the card" in p for p in problems))

    def test_listed_verified_source_passes(self):
        ev = self.tmp / "ev.txt"
        ev.write_text("read", encoding="utf-8")
        sources.add(self.layout, "s1", "https://example.org", "S", "verified", ev, "x",
                    evidence_kind="tool-summary")
        # A card's sources can only change by a new card; use a fresh one.
        make_card(self, "toy2", "supported", extra={"sources": ["s1"]})
        self.layout.notes_path("toy2").write_text("[context] Background. [src:s1]\n", encoding="utf-8")
        report.write_report(self.layout, "toy2")
        v = runner.verify_card(self.layout, "toy2")
        self.assertEqual(report.check_notes(self.layout, "toy2", v), [])
        self.assertEqual(v["level"], 3)

    def test_placeholder_is_open_item_only_in_strict_mode(self):
        notes = "[conjecture] Needs more. DATA_NEEDED\n"
        self.assertEqual(self.check(notes), [])
        self.assertTrue(any("DATA_NEEDED" in p for p in self.check(notes, strict=True)))

    def test_rounding_rule(self):
        ref = [0.319832]
        self.assertTrue(lint._supported("0.32", ref))
        self.assertTrue(lint._supported("0.3198", ref))
        self.assertTrue(lint._supported("0.3", ref))  # a valid one-decimal rounding
        self.assertFalse(lint._supported("0.33", ref))
        self.assertFalse(lint._supported("0.31", ref))  # truncation is not rounding
        self.assertFalse(lint._supported("0.4", ref))


class TestGuard(Base):
    def setUp(self):
        super().setUp()
        (self.tmp / "autosci").mkdir()
        (self.tmp / "autosci" / "core.py").write_text("x = 1\n", encoding="utf-8")
        (self.tmp / "PROTOCOL.md").write_text("rules\n", encoding="utf-8")
        guard.update(self.layout)

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.tmp), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
            capture_output=True, text=True, check=True,
        )

    def test_clean_tree(self):
        self.assertEqual(guard.check_working_tree(self.layout), [])

    def test_edit_detected(self):
        (self.tmp / "autosci" / "core.py").write_text("x = 2\n", encoding="utf-8")
        self.assertTrue(any("changed: autosci/core.py" in p for p in guard.check_working_tree(self.layout)))

    def test_new_file_under_pattern_detected(self):
        (self.tmp / "autosci" / "extra.py").write_text("y = 1\n", encoding="utf-8")
        self.assertTrue(any("new file" in p for p in guard.check_working_tree(self.layout)))

    def test_deleted_file_detected(self):
        (self.tmp / "PROTOCOL.md").unlink()
        self.assertTrue(any("missing" in p for p in guard.check_working_tree(self.layout)))

    def test_base_comparison(self):
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "approved")
        self.assertEqual(guard.check_against_base(self.layout, "HEAD"), [])
        (self.tmp / "autosci" / "core.py").write_text("x = 99\n", encoding="utf-8")
        guard.update(self.layout)  # updating the manifest does not hide the change from the base
        problems = guard.check_against_base(self.layout, "HEAD")
        self.assertTrue(any("changed: autosci/core.py" in p for p in problems))

    def test_pattern_change_flagged(self):
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "approved")
        m = json.loads(self.layout.protected.read_text(encoding="utf-8"))
        m["patterns"] = ["PROTOCOL.md"]
        self.layout.protected.write_text(json.dumps(m), encoding="utf-8")
        self.assertTrue(any("patterns itself changed" in p for p in guard.check_against_base(self.layout, "HEAD")))

    def test_missing_base_manifest_is_reported(self):
        self.git("init", "-q")
        (self.tmp / "other.txt").write_text("a", encoding="utf-8")
        self.git("add", "other.txt")
        self.git("commit", "-q", "-m", "no manifest")
        self.assertTrue(any("no protected manifest" in p for p in guard.check_against_base(self.layout, "HEAD")))


class TestSelftestAndEvolve(Base):
    def setUp(self):
        super().setUp()
        self.cycle()

    def test_selftest_catches_every_applicable_mutation_for_the_intended_reason(self):
        r = selftest.run_selftest(self.tmp, "toy")
        self.assertTrue(r["baseline_clean"], r["baseline_problems"])
        self.assertEqual(r["missed"], [])
        self.assertEqual(r["caught"], r["total"])
        self.assertGreaterEqual(r["total"], 12)
        self.assertTrue(r["blind_spots"])

    def test_selftest_misses_are_reported_when_a_check_is_disabled(self):
        with mock.patch.object(report, "check_notes", return_value=[]):
            r = selftest.run_selftest(self.tmp, "toy")
        self.assertTrue(any("fabricated number" in m for m in r["missed"]))

    def test_gate_rules(self):
        good = {"selftest": {"caught": 13, "total": 13, "missed": [], "baseline_clean": True, "baseline_problems": []},
                "calibration": {"level": 2, "problems": []}, "tests": {"ran": True, "passed": True, "detail": ""}}
        self.assertTrue(evolve.gate(self.layout, good, None)["passes"])
        bad = json.loads(json.dumps(good))
        bad["selftest"].update({"caught": 12, "missed": ["x"]})
        self.assertFalse(evolve.gate(self.layout, bad, None)["passes"])
        bad = json.loads(json.dumps(good))
        bad["calibration"]["level"] = 1
        self.assertFalse(evolve.gate(self.layout, bad, None)["passes"])
        bad = json.loads(json.dumps(good))
        bad["tests"]["passed"] = False
        self.assertFalse(evolve.gate(self.layout, bad, None)["passes"])
        parent = {"benchmark": good}
        lower = json.loads(json.dumps(good))
        lower["selftest"].update({"caught": 12, "total": 13})
        lower["selftest"]["missed"] = []
        self.assertIn("lower than the parent", " ".join(evolve.gate(self.layout, lower, parent)["reasons"]))

    def test_propose_adopt_and_lineage(self):
        with mock.patch.object(evolve, "CALIBRATION_CARD", "toy"):
            a = evolve.propose(self.layout, ["cards/toy.json"], None, "first", run_tests=False)
            self.assertTrue(a["gate"]["passes"], a["gate"]["reasons"])
            with self.assertRaises(evolve.EvolveError):
                evolve.propose(self.layout, ["cards/toy.json"], None, "again", run_tests=False)
            b = evolve.propose(
                self.layout, ["cards/toy.json", "experiments/toy_exp.py"], a["id"], "second", run_tests=False
            )
            self.assertEqual(b["parent"], a["id"])
        evolve.adopt(self.layout, b["id"], "maintainer")
        with self.assertRaises(evolve.EvolveError):
            evolve.adopt(self.layout, b["id"], "maintainer")
        lines = evolve.lineage(self.layout)
        self.assertEqual(len(lines), 2)
        self.assertIn("ADOPTED", lines[1])
        self.assertTrue(lines[1].startswith("  "))
        from autosci import ledger
        self.assertEqual(ledger.verify_chain(self.layout, self.layout.archive), [])

    def test_failed_gate_cannot_be_adopted(self):
        with mock.patch.object(evolve, "CALIBRATION_CARD", "does-not-exist"):
            a = evolve.propose(self.layout, ["cards/toy.json"], None, "broken", run_tests=False)
        self.assertFalse(a["gate"]["passes"])
        with self.assertRaises(evolve.EvolveError):
            evolve.adopt(self.layout, a["id"], "maintainer")


if __name__ == "__main__":
    unittest.main()
