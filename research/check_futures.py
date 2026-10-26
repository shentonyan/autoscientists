"""Causality and raw-to-sample checks for the new futures study."""
import bisect
import math
from pathlib import Path
import unittest
import importlib.util

import futures_data as data


class FuturesChecks(unittest.TestCase):
    def fixture(self):
        bars = [{"time": i * data.STEP, "open": 100 + i, "close": 100.5 + i,
                 "volume": 10, "buy": 4} for i in range(40)]
        metrics = [{"time": i * data.STEP, "oi": 1000 - i} for i in range(40)]
        return bars, metrics, [m["time"] for m in metrics]

    def test_delayed_execution_and_nonoverlapping_label(self):
        bars, metrics, clocks = self.fixture()
        row = data.sample_at(bars, metrics, [], clocks, [], 18)
        self.assertEqual(row["entry_time"] - row["decision_time"], data.STEP)
        self.assertEqual(row["exit_time"] - row["entry_time"], 6 * data.STEP)
        self.assertAlmostEqual(row["forward_return"], 126 / 120 - 1)
        self.assertLessEqual(row["metric_time"] + data.STEP, row["decision_time"])

    def test_future_metric_perturbation_cannot_change_current_sample(self):
        bars, metrics, clocks = self.fixture()
        before = data.sample_at(bars, metrics, [], clocks, [], 18)
        changed = [dict(m) for m in metrics]
        for m in changed[19:]:
            m["oi"] *= 100
        after = data.sample_at(bars, changed, [], clocks, [], 18)
        self.assertEqual(before, after)

    def test_stale_metric_drops_sample(self):
        bars, metrics, clocks = self.fixture()
        self.assertIsNone(data.sample_at(bars, metrics[:15], [], clocks[:15], [], 18))

    def test_funding_entry_inclusive_exit_exclusive(self):
        bars, metrics, clocks = self.fixture()
        settlements = [(20 * data.STEP, 0.0001), (26 * data.STEP, 0.0002)]
        sample = data.sample_at(bars, metrics, settlements, clocks, [x[0] for x in settlements], 18)
        self.assertEqual(sample["funding_short"], 0.0001)

    def test_taker_fraction(self):
        bars, metrics, clocks = self.fixture()
        row = data.sample_at(bars, metrics, [], clocks, [], 18)
        self.assertAlmostEqual(row["flow"], 0.4)

    def test_short_sign_fee_and_cash_on_hand_computed_case(self):
        spec = importlib.util.spec_from_file_location("eventstudy", Path(__file__).resolve().parents[1] / "experiments/aqua_futures_events.py")
        study = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(study)
        config = {"oi_threshold": 0.01, "flow_cut": 0.5}
        row = {"entry_time": 1727740800000, "prior_return": -0.01,
               "rebound": 0.005, "oi_drop": 0.02, "flow": 0.4,
               "forward_return": -0.01, "funding_short": 0.0001}
        result = study.performance([row], config, "full", 1, "2024-10-01", "2025-01-01")
        self.assertAlmostEqual(result["arithmetic_pnl"], 0.0099)
        self.assertEqual(len(result["daily_pnl"]), 92)
        self.assertEqual(result["trades"], 1)
        self.assertEqual(study.performance([row], config, "cash", 1, "2024-10-01", "2025-01-01")["arithmetic_pnl"], 0)

    def test_block_interval_of_zero_signal_is_zero(self):
        spec = importlib.util.spec_from_file_location("eventstudy", Path(__file__).resolve().parents[1] / "experiments/aqua_futures_events.py")
        study = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(study)
        self.assertEqual(study.interval([0] * 92, 1, 50, 7), [0, 0])


def audit_raw(folder):
    """Different scalar route for 64 deterministic rows; shares only inputs."""
    import csv
    bars, metrics, funding, _ = data.load_raw(folder)
    times = {r["time"]: i for i, r in enumerate(bars)}
    with (folder / "samples.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    selected = [rows[i * (len(rows) - 1) // 63] for i in range(64)]
    for row in selected:
        decision = int(row["decision_time"])
        i = times[decision - data.STEP]
        # No feature-builder helpers: scalar filtering by assumed availability.
        snapshots = []
        for offset in (6, 12):
            eligible = [m for m in metrics if m["time"] + data.STEP <= bars[i - offset]["time"] + data.STEP]
            snapshots.append(eligible[-1]["oi"])
        assert abs(float(row["oi_drop"]) - max(0, math.log(snapshots[1] / snapshots[0]))) < 1e-12
        target = bars[i + 8]["open"] / bars[i + 2]["open"] - 1
        assert abs(float(row["forward_return"]) - target) < 1e-12
        vol, buy = 0.0, 0.0
        for j in range(i - 5, i + 1):
            vol += bars[j]["volume"]
            buy += bars[j]["buy"]
        assert abs(float(row["flow"]) - buy / vol) < 1e-12
        reference = sum(rate for stamp, rate in funding
                        if int(row["entry_time"]) <= stamp // 1000 * 1000 < int(row["exit_time"]))
        assert abs(float(row["funding_short"]) - reference) < 1e-12
    return {"independent_raw_sample_checks": 64 * 4, "input_rows_sampled": 64}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--raw":
        import json
        print(json.dumps(audit_raw(data.DEFAULT), indent=2))
    else:
        unittest.main()
