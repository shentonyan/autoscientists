"""Behavior checks for the new pilot, separate from the protected core tests."""
import importlib.util
from pathlib import Path
import unittest
import json
import tempfile

import numpy as np

import quant_pilot as q
from research_memory import ResearchMemory


class PilotChecks(unittest.TestCase):
    def test_search_reuses_prior_candidates_without_reevaluation(self):
        rng = np.random.default_rng(4)
        panel = [{"x": rng.normal(size=(100, 18)), "y": rng.normal(size=100)} for _ in range(3)]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "memory.jsonl"
            m = ResearchMemory(path, "scope", q.validate_candidate)
            first = q.select_factor(panel, "memory", 5, 12, m)
            restored = ResearchMemory(path, "scope", q.validate_candidate)
            second = q.select_factor(panel, "memory", 5, 12, restored)
            self.assertEqual(second["prior_evaluations"], 12)
            self.assertEqual(len(restored.rows), 24)
            initial = [r["candidate"] for r in first["history"]]
            self.assertTrue(all(r["candidate"] not in initial for r in second["history"]))

    def test_cross_run_memory_reloads_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "memory.jsonl"
            memory = ResearchMemory(path, "fixed-scope", q.validate_candidate)
            memory.append({"kind": "momentum", "window": 3, "sign": 1}, 0.04)
            restored = ResearchMemory(path, "fixed-scope", q.validate_candidate)
            self.assertEqual(memory.head, restored.head)
            with self.assertRaises(ValueError):
                ResearchMemory(path, "different-scope", q.validate_candidate)
            row = json.loads(path.read_text())
            row["validation_score"] = 0.99
            path.write_text(json.dumps(row) + "\n")
            with self.assertRaises(ValueError):
                ResearchMemory(path, "fixed-scope", q.validate_candidate)

    def test_memory_has_no_test_result_field(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "memory.jsonl"
            memory = ResearchMemory(path, "scope", q.validate_candidate)
            with self.assertRaises(TypeError):
                memory.append({"kind": "momentum", "window": 3, "sign": 1}, 0.1, test_score=0.9)

    def test_future_changes_do_not_change_past_features(self):
        rng = np.random.default_rng(8)
        close = np.exp(np.cumsum(rng.normal(0, 0.01, 400)))
        a = np.column_stack([np.arange(400) * 300000, close, close, np.ones(400)])
        b = a.copy()
        b[250:, 1:3] *= 10
        b[250:, 3] *= 100
        np.testing.assert_array_equal(q.features(a)[:250], q.features(b)[:250])

    def test_target_uses_next_open_and_splits_purge_label_end(self):
        size = 1000
        t = 1714521600000 + np.arange(size) * 300000
        opening = np.arange(size) + 100.0
        a = np.column_stack([t, opening, opening + 0.5, np.ones(size)])
        data = q.samples({"X": a})["test"][0]
        self.assertAlmostEqual(data["y"][0], opening[103] / opening[97] - 1)
        self.assertEqual(data["time"][0], t[97])
        boundary = 1714521600000
        a[:, 0] = boundary - 500 * 300000 + np.arange(size) * 300000
        val = q.samples({"X": a})["validation"][0]
        self.assertTrue(np.all(val["time"] + q.HORIZON * 300000 < boundary))

    def test_round_trip_cost_includes_final_liquidation(self):
        panel = [{"y": np.zeros(3)}, {"y": np.zeros(3)}]
        output = q.portfolio(panel, [np.ones(3), -np.ones(3)], 1)
        # Constant gross exposure 1: one entry and one exit, no rebalancing.
        expected = (1 - 0.0001) ** 2 - 1
        self.assertAlmostEqual(output["net_return"], expected, places=12)

    def test_rank_ties(self):
        np.testing.assert_array_equal(q.ranks(np.array([5, 2, 2, 8])), [2, 0.5, 0.5, 3])

    def test_candidate_rejects_extra_keys_and_bad_types(self):
        for value in ({"kind": "eval", "window": 3, "sign": 1},
                      {"kind": "momentum", "window": 3, "sign": True},
                      {"kind": "momentum", "window": 3, "sign": 1, "code": "exec"}):
            with self.assertRaises(ValueError):
                q.validate_candidate(value)

    def test_auction_memory_is_not_given_test_data(self):
        spec = importlib.util.spec_from_file_location("auction", Path(__file__).resolve().parents[1] / "experiments/aqua_search.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        values = [0.2, 0.4, 0.8] * 200
        opponents = [0.1, 0.3, 0.45] * 200
        a = module.search("random", 12, values, opponents, 1)
        b = module.search("no_memory", 12, values, opponents, 1)
        self.assertEqual(a, b)
        self.assertEqual(a["evaluations"], 12)


if __name__ == "__main__":
    unittest.main()
