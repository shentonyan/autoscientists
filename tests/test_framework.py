"""Tests for the guarantees the framework claims.

Each test breaks something on purpose and checks that verification notices.
A tiny experiment is used so the suite runs in well under a second.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from autosci import card as cardlib
from autosci import ledger, report, runner, sources
from autosci.paths import Layout

EXPERIMENT = '''
import random

def run(params, seed):
    rng = random.Random(seed)
    xs = [rng.random() for _ in range(params["n"])]
    return {"mean": round(sum(xs) / len(xs), 12)}

def evaluate(params, per_seed):
    m = sum(r["mean"] for r in per_seed.values()) / len(per_seed)
    return {"H1": {"verdict": "supported" if abs(m - 0.5) < 0.05 else "refuted",
                   "detail": {"pooled_mean": m}}}

def crosscheck(params, per_seed):
    m = sum(r["mean"] for r in per_seed.values()) / len(per_seed)
    return [{"name": "mean near 1/2", "observed": m, "reference": 0.5,
             "tolerance": 0.05, "ok": abs(m - 0.5) < 0.05}]
'''

CARD = {
    "id": "toy",
    "title": "Toy card",
    "question": "Is the mean of U[0,1] about one half?",
    "experiment": "toy_exp",
    "params": {"n": 2000},
    "seeds": [1, 2, 3],
    "hypotheses": [
        {
            "id": "H1",
            "statement": "The pooled mean is within 0.05 of 0.5.",
            "falsifier": "The pooled mean differs from 0.5 by 0.05 or more.",
            "predicted_verdict": "supported",
        }
    ],
    "sources": [],
}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.layout = Layout(self.tmp)
        self.layout.cards.mkdir()
        self.layout.experiments.mkdir()
        self.layout.experiment_path("toy_exp").write_text(EXPERIMENT, encoding="utf-8")
        self.layout.card_path("toy").write_text(json.dumps(CARD), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cycle(self):
        cardlib.lock(self.layout, "toy")
        runner.run_card(self.layout, "toy")
        return report.write_report(self.layout, "toy")


class TestCard(Base):
    def test_valid_card(self):
        self.assertEqual(cardlib.validate(CARD), [])

    def test_missing_falsifier_rejected(self):
        bad = json.loads(json.dumps(CARD))
        bad["hypotheses"][0]["falsifier"] = " "
        self.assertTrue(any("falsifier" in p for p in cardlib.validate(bad)))

    def test_duplicate_seeds_rejected(self):
        bad = dict(CARD, seeds=[1, 1])
        self.assertTrue(any("distinct" in p for p in cardlib.validate(bad)))

    def test_run_requires_lock(self):
        with self.assertRaises(runner.RunError):
            runner.run_card(self.layout, "toy")

    def test_lock_is_immutable(self):
        cardlib.lock(self.layout, "toy")
        changed = dict(CARD, seeds=[9])
        self.layout.card_path("toy").write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaises(cardlib.CardError):
            cardlib.lock(self.layout, "toy")

    def test_card_edit_after_lock_detected(self):
        cardlib.lock(self.layout, "toy")
        changed = dict(CARD, params={"n": 5})
        self.layout.card_path("toy").write_text(json.dumps(changed), encoding="utf-8")
        self.assertIn("card changed after lock", cardlib.check_lock(self.layout, "toy"))
        with self.assertRaises(runner.RunError):
            runner.run_card(self.layout, "toy")

    def test_experiment_edit_after_lock_detected(self):
        cardlib.lock(self.layout, "toy")
        p = self.layout.experiment_path("toy_exp")
        p.write_text(EXPERIMENT + "\n# tweak\n", encoding="utf-8")
        self.assertIn(
            "experiment source changed after lock", cardlib.check_lock(self.layout, "toy")
        )


class TestVerify(Base):
    def test_clean_cycle_verifies_at_level_2(self):
        _, v = self.cycle()
        self.assertEqual(v["problems"], [])
        self.assertEqual(v["level"], 2)
        again = runner.verify_card(self.layout, "toy")
        self.assertEqual(again["problems"], [])
        self.assertEqual(report.check_report_current(self.layout, "toy", again), [])

    def test_run_is_reproducible(self):
        self.cycle()
        a = runner.run_card(self.layout, "toy")
        b = runner.run_card(self.layout, "toy")
        self.assertEqual(a["run_id"], b["run_id"])
        self.assertEqual(len(ledger.runs_for_card(self.layout, "toy")), 1)

    def test_tampered_run_file_detected(self):
        self.cycle()
        rf = next(self.layout.runs.glob("*.json"))
        data = json.loads(rf.read_text(encoding="utf-8"))
        data["results"]["1"]["mean"] = 0.5
        rf.write_text(json.dumps(data), encoding="utf-8")
        v = runner.verify_card(self.layout, "toy")
        self.assertTrue(any("do not match the ledger" in p for p in v["problems"]))
        self.assertEqual(v["level"], 0)

    def test_tampered_ledger_detected(self):
        self.cycle()
        lines = self.layout.ledger.read_text(encoding="utf-8").splitlines()
        entry = json.loads(lines[0])
        entry["results_sha256"] = "0" * 64
        self.layout.ledger.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        self.assertTrue(ledger.verify_chain(self.layout))

    def test_deleted_entry_breaks_chain(self):
        self.cycle()
        ledger.append(self.layout, {"type": "note", "text": "second"})
        ledger.append(self.layout, {"type": "note", "text": "third"})
        lines = self.layout.ledger.read_text(encoding="utf-8").splitlines()
        self.layout.ledger.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")
        self.assertTrue(ledger.verify_chain(self.layout))

    def test_hand_edited_report_detected(self):
        self.cycle()
        p = self.layout.report_path("toy")
        p.write_text(p.read_text(encoding="utf-8").replace("supported", "refuted"), encoding="utf-8")
        v = runner.verify_card(self.layout, "toy")
        extra = report.check_report_current(self.layout, "toy", v)
        self.assertTrue(extra)

    def test_failed_crosscheck_blocks_verification(self):
        bad = EXPERIMENT.replace('"ok": abs(m - 0.5) < 0.05}', '"ok": False}')
        self.layout.experiment_path("toy_exp").write_text(bad, encoding="utf-8")
        cardlib.lock(self.layout, "toy")
        runner.run_card(self.layout, "toy")
        v = runner.verify_card(self.layout, "toy")
        self.assertTrue(any("cross-check failed" in p for p in v["problems"]))
        self.assertEqual(v["level"], 0)

    def test_missing_crosscheck_blocks_verification(self):
        bad = EXPERIMENT.replace(
            "def crosscheck(params, per_seed):", "def crosscheck(params, per_seed):\n    return []\n\ndef _unused(params, per_seed):"
        )
        self.layout.experiment_path("toy_exp").write_text(bad, encoding="utf-8")
        cardlib.lock(self.layout, "toy")
        runner.run_card(self.layout, "toy")
        v = runner.verify_card(self.layout, "toy")
        self.assertTrue(any("no independent cross-check" in p for p in v["problems"]))

    def test_evaluate_must_cover_exactly_the_registered_hypotheses(self):
        bad = EXPERIMENT.replace('return {"H1":', 'return {"H9":')
        self.layout.experiment_path("toy_exp").write_text(bad, encoding="utf-8")
        cardlib.lock(self.layout, "toy")
        with self.assertRaises(runner.RunError):
            runner.run_card(self.layout, "toy")


class TestSources(Base):
    def test_unverified_source_cannot_be_cited(self):
        sources.add(self.layout, "lead1", "https://example.org/a", "A lead", "unverified")
        with self.assertRaises(sources.SourceError):
            sources.cite(self.layout, "lead1")

    def test_verified_source_needs_evidence_text(self):
        with self.assertRaises(sources.SourceError):
            sources.add(self.layout, "s1", "https://example.org/b", "B", "verified")

    def test_verified_source_with_evidence_is_citable_and_lifts_level(self):
        ev = self.tmp / "evidence.txt"
        ev.write_text("passage that was actually read", encoding="utf-8")
        sources.add(self.layout, "s1", "https://example.org/b", "B", "verified", ev, "toy claim")
        self.assertEqual(sources.cite(self.layout, "s1")["id"], "s1")
        withsrc = dict(CARD, sources=["s1"])
        self.layout.card_path("toy").write_text(json.dumps(withsrc), encoding="utf-8")
        _, v = self.cycle()
        self.assertEqual(v["level"], 3)

    def test_card_citing_unverified_source_cannot_pass(self):
        sources.add(self.layout, "lead1", "https://example.org/a", "A lead", "unverified")
        withsrc = dict(CARD, sources=["lead1"])
        self.layout.card_path("toy").write_text(json.dumps(withsrc), encoding="utf-8")
        cardlib.lock(self.layout, "toy")
        runner.run_card(self.layout, "toy")
        v = runner.verify_card(self.layout, "toy")
        self.assertTrue(any("source problem" in p for p in v["problems"]))
        self.assertEqual(v["level"], 0)


class TestShippedCalibration(unittest.TestCase):
    """The committed calibration card must still verify against the committed ledger."""

    def test_committed_calibration_verifies(self):
        layout = Layout()
        if not layout.lock_path("auction-calibration").exists():
            self.skipTest("calibration card not locked in this checkout")
        v = runner.verify_card(layout, "auction-calibration")
        self.assertEqual(v["problems"], [])
        self.assertGreaterEqual(v["level"], 2)
        self.assertEqual(report.check_report_current(layout, "auction-calibration", v), [])


if __name__ == "__main__":
    unittest.main()
