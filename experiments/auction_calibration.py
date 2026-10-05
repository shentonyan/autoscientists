"""Calibration experiment: two sealed-bid auctions whose answers are known.

Two bidders, private values and opponent draws uniform on [0, 1].

Second-price (Vickrey): bidding one's value weakly dominates every other bid, so
the per-sample gain from any deviation is never positive. Against an opponent
bid x ~ U[0,1], expected utility of bid b with value v is  v*b - b^2/2.

First-price against the equilibrium opponent (bid = x/2): expected utility of
bid b is  (v - b) * min(2b, 1), maximised at b = v/2, and truthful bidding
yields exactly zero.

The purpose is not new knowledge. It is to check that the loop reproduces
results that are known, and refutes a hypothesis that is known to be false,
before the loop is pointed at questions whose answers are not known.

`run` simulates. `crosscheck` uses only the closed forms above, so the two
share no code.
"""
from __future__ import annotations

import math
import random

Z95 = 1.96
SE_TOL = 4.0  # cross-check tolerance, in pooled standard errors
EPS = 1e-12


def _grid(params):
    n = params["bid_steps"]
    return n, [i / n for i in range(n + 1)]


def _values(params):
    n = params["bid_steps"]
    return [round(k / n, 12) for k in params["value_indices"]]


def _simulate(mechanism: str, params: dict, seed: int) -> dict:
    rng = random.Random(seed)
    n_steps, bids = _grid(params)
    values = _values(params)
    n = params["n_samples"]
    sums = {v: [0.0] * len(bids) for v in values}
    sqs = {v: [0.0] * len(bids) for v in values}
    violations = 0
    max_gain = 0.0

    for _ in range(n):
        x = rng.random()
        opp = x if mechanism == "second_price" else x / 2.0
        for v in values:
            su, sq = sums[v], sqs[v]
            truthful = (v - opp) if v > opp else 0.0
            for j, b in enumerate(bids):
                if b > opp:
                    u = (v - opp) if mechanism == "second_price" else (v - b)
                else:
                    u = 0.0
                su[j] += u
                sq[j] += u * u
                if mechanism == "second_price":
                    gain = u - truthful
                    if gain > EPS:
                        violations += 1
                    if gain > max_gain:
                        max_gain = gain

    out = {}
    for v in values:
        means = [s / n for s in sums[v]]
        ses = [
            math.sqrt(max(sq / n - m * m, 0.0) / n)
            for sq, m in zip(sqs[v], means)
        ]
        out[str(v)] = {
            "mean_u": [round(m, 12) for m in means],
            "se_u": [round(s, 12) for s in ses],
        }
    res = {"values": out}
    if mechanism == "second_price":
        res["violations"] = violations
        res["max_gain"] = round(max_gain, 12)
        res["comparisons"] = n * len(values) * len(bids)
    return res


def run(params: dict, seed: int) -> dict:
    return {
        "second_price": _simulate("second_price", params, seed),
        "first_price": _simulate("first_price", params, seed + 1_000_003),
    }


def _pool(per_seed: dict, mechanism: str, v: float):
    """Pooled mean and standard error per bid index across seeds."""
    k = len(per_seed)
    cols = [per_seed[s][mechanism]["values"][str(v)] for s in sorted(per_seed)]
    n_bids = len(cols[0]["mean_u"])
    means, ses = [], []
    for j in range(n_bids):
        means.append(sum(c["mean_u"][j] for c in cols) / k)
        ses.append(math.sqrt(sum(c["se_u"][j] ** 2 for c in cols)) / k)
    return means, ses


def _bid_index(params: dict, bid: float) -> int:
    n_steps, bids = _grid(params)
    return min(range(len(bids)), key=lambda j: abs(bids[j] - bid))


def evaluate(params: dict, per_seed: dict) -> dict:
    values = _values(params)

    # H1: second-price truthfulness is a weakly dominant strategy.
    total_viol = sum(per_seed[s]["second_price"]["violations"] for s in per_seed)
    total_cmp = sum(per_seed[s]["second_price"]["comparisons"] for s in per_seed)
    max_gain = max(per_seed[s]["second_price"]["max_gain"] for s in per_seed)
    h1 = {
        "verdict": "supported" if total_viol == 0 else "refuted",
        "detail": {
            "violations": total_viol,
            "comparisons": total_cmp,
            "max_single_sample_gain": max_gain,
        },
    }

    # H2: first-price, truthful bidding is not a best response (bid v/2 beats it).
    # H3: first-price, truthful bidding earns positive expected utility.
    lows2, highs3, lows3 = [], [], []
    d2, d3 = {}, {}
    for v in values:
        means, ses = _pool(per_seed, "first_price", v)
        j_half = _bid_index(params, v / 2)
        j_truth = _bid_index(params, v)
        gain = means[j_half] - means[j_truth]
        se_gain = math.sqrt(ses[j_half] ** 2 + ses[j_truth] ** 2)
        lows2.append(gain - Z95 * se_gain)
        d2[f"v={v}: gain of bidding v/2 over v (mean)"] = gain
        d2[f"v={v}: 95% lower bound"] = gain - Z95 * se_gain
        lows3.append(means[j_truth] - Z95 * ses[j_truth])
        highs3.append(means[j_truth] + Z95 * ses[j_truth])
        d3[f"v={v}: truthful expected utility (mean)"] = means[j_truth]
        d3[f"v={v}: 95% upper bound"] = means[j_truth] + Z95 * ses[j_truth]

    h2 = {
        "verdict": "supported" if all(l > 0 for l in lows2) else "inconclusive",
        "detail": d2,
    }
    if all(l > 0 for l in lows3):
        v3 = "supported"
    elif all(h <= 0 for h in highs3):
        v3 = "refuted"
    else:
        v3 = "inconclusive"
    h3 = {"verdict": v3, "detail": d3}
    return {"H1": h1, "H2": h2, "H3": h3}


def _analytic(mechanism: str, v: float, b: float) -> float:
    if mechanism == "second_price":
        return v * b - b * b / 2.0 if b <= 1.0 else v - 0.5
    return (v - b) * min(2.0 * b, 1.0)


def crosscheck(params: dict, per_seed: dict) -> list:
    n_steps, bids = _grid(params)
    checks = []
    for mechanism in ("second_price", "first_price"):
        worst_ratio, n_points, bad = 0.0, 0, 0
        argmax_ok = True
        for v in _values(params):
            means, ses = _pool(per_seed, mechanism, v)
            for j, b in enumerate(bids):
                ref = _analytic(mechanism, v, b)
                tol = SE_TOL * ses[j] + 1e-9
                diff = abs(means[j] - ref)
                n_points += 1
                worst_ratio = max(worst_ratio, diff / tol)
                if diff > tol:
                    bad += 1
            ref_best = max(range(len(bids)), key=lambda j: _analytic(mechanism, v, bids[j]))
            obs_best = max(range(len(bids)), key=lambda j: means[j])
            if ref_best != obs_best:
                argmax_ok = False
        checks.append(
            {
                "name": f"{mechanism}: simulated expected utility vs closed form "
                f"at {n_points} (value, bid) points",
                "observed": bad,
                "reference": 0,
                "tolerance": f"{SE_TOL} pooled standard errors per point",
                "ok": bad == 0,
            }
        )
        checks.append(
            {
                "name": f"{mechanism}: best bid on the grid matches the closed-form optimum for every value",
                "observed": argmax_ok,
                "reference": True,
                "tolerance": "exact grid index",
                "ok": argmax_ok,
            }
        )
    # Exact identity: truthful bidding in first price pays exactly zero.
    for v in _values(params):
        means, ses = _pool(per_seed, "first_price", v)
        j = _bid_index(params, v)
        checks.append(
            {
                "name": f"first_price: truthful utility is exactly 0 at v={v}",
                "observed": means[j],
                "reference": 0.0,
                "tolerance": 1e-12,
                "ok": abs(means[j]) <= 1e-12,
            }
        )
    return checks
