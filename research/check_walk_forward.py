"""Behavioral checks for the frozen walk-forward research protocol."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest
import csv
import hashlib
import tempfile
from datetime import date, timedelta

spec = importlib.util.spec_from_file_location("walkstudy", Path(__file__).resolve().parents[1] / "experiments/aqua_walk_forward.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class WalkChecks(unittest.TestCase):
    def test_future_return_changes_cannot_change_earlier_selection(self):
        rows = []
        day = date(2024, 7, 1)
        while day < date(2026, 1, 1):
            time = study.stamp(day.isoformat()) + 12 * 3600000
            i = len(rows)
            rows.append({"split": "synthetic", "decision_time": time - 300000,
                         "entry_time": time, "exit_time": time + 1800000,
                         "metric_time": time - 600000, "oi_drop": 0.001 * (i % 20 + 1),
                         "prior_return": -0.01, "rebound": 0.002,
                         "flow": 0.4 if i % 2 else 0.6, "forward_return": -0.004,
                         "funding_short": 0.0})
            day += timedelta(days=1)
        with tempfile.TemporaryDirectory() as temp:
            results = []
            for version in (0, 1):
                path = Path(temp) / f"rows-{version}.csv"
                changed = [dict(r) for r in rows]
                if version:
                    for r in changed:
                        if r["decision_time"] >= study.stamp("2025-04-01"):
                            r["forward_return"] = 0.25
                with path.open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(changed)
                params = {"sample_files": [str(path)], "input_hashes": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()},
                          "quantiles": [0.7, 0.9], "cost_bps": 2, "stress_cost_bps": 5,
                          "min_validation_trades": 1, "bootstrap_repetitions": 20, "block_days": 14}
                results.append(study.run(params, 1))
            self.assertEqual(results[0]["folds"][0]["frozen"], results[1]["folds"][0]["frozen"])
            self.assertNotEqual(results[0]["arithmetic_pnl"], results[1]["arithmetic_pnl"])

    def test_split_boundary_purges_target(self):
        boundary = study.stamp("2025-04-01")
        rows = [{"decision_time": boundary - 600000, "exit_time": boundary + 600000},
                {"decision_time": boundary - 3000000, "exit_time": boundary - 600000},
                {"decision_time": boundary + 300000, "exit_time": boundary + 2400000}]
        old = study.section(rows, "2025-01-01", "2025-04-01")
        new = study.section(rows, "2025-04-01", "2025-07-01")
        self.assertEqual(old, [rows[1]])
        self.assertEqual(new, [rows[2]])

    def test_cash_cannot_trade(self):
        row = {"prior_return": -0.01, "rebound": 0.002, "oi_drop": 0.03, "flow": 0.8}
        self.assertFalse(study.active(row, {"flow": "cash", "threshold": 0}))
        self.assertTrue(study.active(row, {"flow": "strong", "threshold": 0.01}))
        self.assertFalse(study.active(row, {"flow": "weak", "threshold": 0.01}))

    def test_known_short_cost_and_score(self):
        row = {"entry_time": study.stamp("2025-04-02"), "prior_return": -0.01,
               "rebound": 0.002, "oi_drop": 0.03, "flow": 0.8,
               "forward_return": -0.01, "funding_short": 0.0001}
        config = {"flow": "strong", "threshold": 0.01}
        low = study.evaluate_policy([row], config, 2, "2025-04-01", "2025-07-01")
        high = study.evaluate_policy([row], config, 5, "2025-04-01", "2025-07-01")
        self.assertAlmostEqual(low["arithmetic_pnl"], 0.0097)
        self.assertAlmostEqual(high["arithmetic_pnl"] - low["arithmetic_pnl"], -0.0006)
        self.assertLess(low["selection_score"], low["mean"])

    def test_heldout_quarters_are_disjoint(self):
        for _, start, end in study.FOLDS:
            self.assertLess(study.stamp(start), study.stamp(end))
        self.assertEqual(study.FOLDS[0][2], study.FOLDS[1][1])
        self.assertEqual(study.FOLDS[1][2], study.FOLDS[2][1])

    def test_zero_bootstrap(self):
        self.assertEqual(study.bootstrap([0] * 30, 1, 50, 7), [0, 0])


if __name__ == "__main__":
    unittest.main()
