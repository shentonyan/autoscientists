"""Locked, stdlib-only OI/rebound/flow experiment on pinned public samples.

This module contains all selection and evaluation code. Input CSV and builder
source hashes are explicit preregistered dependencies, checked on every run.
"""
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parents[1]


def read_data(params):
    for key in ("samples", "builder"):
        path = ROOT / params[key]
        if hashlib.sha256(path.read_bytes()).hexdigest() != params[key + "_sha256"]:
            raise ValueError(f"preregistered {key} changed")
    parts = {key: [] for key in ("train", "validation", "test")}
    with (ROOT / params["samples"]).open(encoding="utf-8") as stream:
        for raw in csv.DictReader(stream):
            split = raw.pop("split")
            row = {key: float(value) for key, value in raw.items()}
            if not all(math.isfinite(x) for x in row.values()):
                raise ValueError("nonfinite sample")
            if not row["metric_time"] + 300000 <= row["decision_time"] < row["entry_time"] < row["exit_time"]:
                raise ValueError("invalid information/entry/exit ordering")
            parts[split].append(row)
    return parts


def quantile(values, probability):
    values = sorted(values)
    index = (len(values) - 1) * probability
    left = int(index)
    right = min(left + 1, len(values) - 1)
    return values[left] + (values[right] - values[left]) * (index - left)


def trade(row, config, policy):
    price = row["prior_return"] < 0 and row["rebound"] > 0
    oi = row["oi_drop"] > config["oi_threshold"]
    flow = row["flow"] < config["flow_cut"]
    if policy == "cash":
        return False
    return price and {"price_only": True, "oi_only": oi, "flow_only": flow,
                      "full": oi and flow}[policy]


def performance(rows, config, policy, cost, start, end):
    day = date.fromisoformat(start)
    stop = date.fromisoformat(end)
    daily = {}
    while day < stop:
        daily[day.isoformat()] = 0.0
        day += timedelta(days=1)
    count = 0
    total_funding = 0.0
    for row in rows:
        if trade(row, config, policy):
            value = -row["forward_return"] + row["funding_short"] - 2 * cost / 10000
            key = datetime.fromtimestamp(row["entry_time"] / 1000, timezone.utc).date().isoformat()
            daily[key] += value
            total_funding += row["funding_short"]
            count += 1
    values = list(daily.values())
    # One unit of initial notional per trade, with no reinvestment. Daily PNL
    # addition is arithmetic, not a compounded NAV or leveraged trading claim.
    sd = statistics.stdev(values)
    cumulative = peak = 0.0
    drawdown = 0.0
    for pnl in values:
        cumulative += pnl
        peak = max(peak, cumulative)
        drawdown = min(drawdown, cumulative - peak)
    return {"trades": count, "daily_pnl": daily, "arithmetic_pnl": sum(values),
            "mean_daily_pnl": statistics.mean(values), "funding_pnl": total_funding,
            "annualized_daily_sharpe": statistics.mean(values) / sd * math.sqrt(365) if sd else 0.0,
            "max_arithmetic_drawdown": drawdown}


def interval(values, seed, repetitions, block):
    rng = random.Random(seed)
    n = len(values)
    draws = []
    for _ in range(repetitions):
        sample = []
        while len(sample) < n:
            start = rng.randrange(n)
            sample.extend(values[(start + j) % n] for j in range(block))
        draws.append(statistics.mean(sample[:n]))
    return [quantile(draws, 0.025), quantile(draws, 0.975)]


def run(params, seed):
    parts = read_data(params)
    history = []
    for q in params["oi_quantiles"]:
        threshold = quantile([r["oi_drop"] for r in parts["train"]], q)
        for flow in params["flow_cuts"]:
            config = {"oi_quantile": q, "oi_threshold": threshold, "flow_cut": flow}
            score = performance(parts["validation"], config, "full", params["cost_bps"], "2024-09-01", "2024-10-01")
            history.append({"config": config, "validation_mean_daily_pnl": score["mean_daily_pnl"],
                            "validation_trades": score["trades"]})
    eligible = [r for r in history if r["validation_trades"] >= params["min_validation_trades"]]
    winner = max(eligible or history, key=lambda row: row["validation_mean_daily_pnl"])
    config = winner["config"]
    # Select the reference on validation, never by its test ranking.
    baselines = {}
    for policy in ("cash", "price_only", "oi_only", "flow_only"):
        baselines[policy] = performance(parts["validation"], config, policy, params["cost_bps"],
                                        "2024-09-01", "2024-10-01")["mean_daily_pnl"]
    reference = max(baselines, key=baselines.get)
    selection = {"config": config, "validation_history": history,
                 "validation_reference_scores": baselines, "reference": reference,
                 "eligible": bool(eligible)}
    selection_hash = hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest()
    # No test metrics have been computed above this boundary.
    test = {policy: performance(parts["test"], config, policy, params["cost_bps"], "2024-10-01", "2025-01-01")
            for policy in ("cash", "price_only", "oi_only", "flow_only", "full")}
    sensitivity = {str(cost): performance(parts["test"], config, "full", cost, "2024-10-01", "2025-01-01")["arithmetic_pnl"]
                   for cost in (0, 1, 2, 5)}
    full = list(test["full"]["daily_pnl"].values())
    ref = list(test[reference]["daily_pnl"].values())
    differences = [a - b for a, b in zip(full, ref)]
    return {"selection": selection, "selection_sha256": selection_hash, "test": test,
            "cost_sensitivity_arithmetic_pnl": sensitivity,
            "full_mean_interval": interval(full, seed, params["bootstrap_repetitions"], params["block_days"]),
            "incremental_mean_interval": interval(differences, seed, params["bootstrap_repetitions"], params["block_days"]),
            "mean_incremental_daily_pnl": statistics.mean(differences),
            "test_days": len(full), "test_samples": len(parts["test"])}


def evaluate(params, per_seed):
    row = next(iter(per_seed.values()))
    def verdict(bounds):
        if not row["selection"]["eligible"] or row["test"]["full"]["trades"] < params["min_test_trades"]:
            return "inconclusive"
        return "supported" if bounds[0] > 0 else "refuted" if bounds[1] < 0 else "inconclusive"
    return {"H1": {"verdict": verdict(row["full_mean_interval"]),
                   "detail": {"test_trades": row["test"]["full"]["trades"],
                              "arithmetic_pnl": row["test"]["full"]["arithmetic_pnl"],
                              "mean_daily_pnl": row["test"]["full"]["mean_daily_pnl"],
                              "interval": row["full_mean_interval"], "test_days": row["test_days"]}},
            "H2": {"verdict": verdict(row["incremental_mean_interval"]),
                   "detail": {"reference": row["selection"]["reference"],
                              "incremental_mean_daily_pnl": row["mean_incremental_daily_pnl"],
                              "interval": row["incremental_mean_interval"]}},
            "H3": {"verdict": "refuted" if row["test"]["full"]["trades"] > 0 else "inconclusive",
                   "detail": {"cost_1bp_pnl": row["cost_sensitivity_arithmetic_pnl"]["1"],
                              "cost_5bp_pnl": row["cost_sensitivity_arithmetic_pnl"]["5"]}}}


def crosscheck(params, per_seed):
    # Independent scalar aggregation, sharing only the pinned sample inputs and
    # selected configuration. Does not call trade(), performance() or interval().
    with (ROOT / params["samples"]).open(encoding="utf-8") as stream:
        records = [r for r in csv.DictReader(stream) if r["split"] == "test"]
    config = next(iter(per_seed.values()))["selection"]["config"]
    observed = next(iter(per_seed.values()))
    checks = []
    for policy in ("cash", "price_only", "oi_only", "flow_only", "full"):
        total, trades = 0.0, 0
        for r in records:
            conditions = [float(r["prior_return"]) < 0, float(r["rebound"]) > 0]
            if policy in ("oi_only", "full"):
                conditions.append(float(r["oi_drop"]) > config["oi_threshold"])
            if policy in ("flow_only", "full"):
                conditions.append(float(r["flow"]) < config["flow_cut"])
            if policy != "cash" and all(conditions):
                trades += 1
                total += float(r["funding_short"]) - float(r["forward_return"]) - params["cost_bps"] / 5000
        result = observed["test"][policy]
        checks.append({"name": policy + " independently aggregated short PNL and trade count",
                       "observed": result["arithmetic_pnl"], "reference": total,
                       "tolerance": 1e-10, "ok": abs(total - result["arithmetic_pnl"]) < 1e-10 and result["trades"] == trades})
    expected_delta = -0.0008 * observed["test"]["full"]["trades"]
    actual_delta = observed["cost_sensitivity_arithmetic_pnl"]["5"] - observed["cost_sensitivity_arithmetic_pnl"]["1"]
    checks.append({"name": "higher round-trip fee obeys closed-form PNL decrement",
                   "observed": actual_delta, "reference": expected_delta,
                   "tolerance": 1e-10, "ok": abs(expected_delta - actual_delta) < 1e-10})
    return checks
