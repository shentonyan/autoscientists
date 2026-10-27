"""Synthetic causality and accounting checks; no market-performance queries."""
import unittest
import numpy as np
from prepare_equity import feature_grid, planned_months
from equity_metrics import account, weights, select


class EquityChecks(unittest.TestCase):
    def test_future_changes_do_not_change_past_features(self):
        price = 100 + np.arange(390) / 100
        grid = np.column_stack((price, price + 1, price - 1, price + .1, price * 100))
        before = feature_grid(grid)
        grid[200:] *= 2
        np.testing.assert_allclose(before[:200], feature_grid(grid)[:200], equal_nan=True)

    def test_no_embargo_or_unavailable_month(self):
        months = planned_months()
        self.assertEqual(len(months), 175)
        self.assertFalse(any(s.startswith("2020") for s in months))
        self.assertEqual(months[-1], "2025-07")

    def test_contiguous_weights_are_netted(self):
        w = np.array([[.5, -.5], [.5, -.5]])
        y = np.array([[.02, -.02], [.01, -.01]])
        pnl, turnover = account(w, y, np.array([0, 30]), np.array([30, 60]), .001)
        np.testing.assert_allclose(turnover, [1, 1])
        self.assertAlmostEqual(pnl.sum(), .028)

    def test_gap_closes_and_reopens(self):
        w = np.array([[.5, -.5], [.5, -.5]])
        pnl, turnover = account(w, np.zeros_like(w), np.array([0, 90]), np.array([30, 120]), .001)
        np.testing.assert_allclose(turnover, [2, 2])
        self.assertAlmostEqual(pnl.sum(), -.004)

    def test_overlap_rejected(self):
        with self.assertRaises(ValueError):
            account(np.zeros((2, 4)), np.zeros((2, 4)), np.array([0, 20]), np.array([30, 50]), .001)

    def test_cash_ties_and_costs(self):
        p = np.ones((101, 4))
        np.testing.assert_array_equal(weights(p, 0), np.zeros_like(p))
        selection = select(p, np.zeros_like(p), np.arange(101) * 30, np.arange(1, 102) * 30)
        self.assertIsNone(selection["cutoff"])


if __name__ == "__main__":
    unittest.main()
