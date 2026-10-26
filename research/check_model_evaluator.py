"""Hand-computed tests for forecast confirmation; no actual holdout inspection."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("model_eval", Path(__file__).resolve().parents[1] / "experiments/aqua_hybrid_confirmation.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


class ModelChecks(unittest.TestCase):
    def test_pearson_known_cases(self):
        self.assertAlmostEqual(evaluation.correlation([1, 2, 3], [3, 5, 7]), 1)
        self.assertAlmostEqual(evaluation.correlation([1, 2, 3], [7, 5, 3]), -1)
        self.assertEqual(evaluation.correlation([1, 1, 1], [2, 3, 4]), 0)

    def test_long_short_funding_sign_and_roundtrip_cost(self):
        rows = [{"entry_time": 1767225600000, "prediction": 0.02, "forward_return": 0.01, "funding_short": 0.0001},
                {"entry_time": 1767227400000, "prediction": -0.02, "forward_return": -0.01, "funding_short": 0.0001}]
        result = evaluation.strategy(rows, "prediction", 1, 0.01, 2)
        self.assertAlmostEqual(result["pnl"], 0.0192)
        self.assertEqual(result["trades"], 2)
        empty = evaluation.strategy(rows, "prediction", 1, float("inf"), 2)
        self.assertEqual(empty["pnl"], 0)

    def test_validation_losses_trigger_abstention(self):
        rows = [{"entry_time": 1759276800000 + i * 1800000, "model": i + 1.0,
                 "forward_return": i * 1e-10, "funding_short": 0.0} for i in range(100)]
        choice = evaluation.choose(rows, "model", {"threshold_quantiles": [0.8, 0.9], "min_validation_trades": 1, "cost_bps": 2})
        self.assertTrue(choice["abstain"])


if __name__ == "__main__":
    unittest.main()
