"""Frozen quarterly walk-forward policy search; no test-driven policy revision."""
import csv
from datetime import datetime, timezone, date, timedelta
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parents[1]
FOLDS = (("2025-01-01", "2025-04-01", "2025-07-01"),
         ("2025-04-01", "2025-07-01", "2025-10-01"),
         ("2025-07-01", "2025-10-01", "2026-01-01"))


def stamp(day):
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)


def read_rows(params):
    for file, expected in params["input_hashes"].items():
        if hashlib.sha256((ROOT / file).read_bytes()).hexdigest() != expected:
            raise ValueError("pinned dependency changed: " + file)
    rows = []
    for filename in params["sample_files"]:
        with (ROOT / filename).open(encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                row.pop("split")
                row = {k: float(v) for k, v in row.items()}
                if not all(math.isfinite(v) for v in row.values()):
                    raise ValueError("nonfinite input")
                if row["metric_time"] + 300000 > row["decision_time"] or row["entry_time"] - row["decision_time"] != 300000:
                    raise ValueError("noncausal timing")
                rows.append(row)
    rows.sort(key=lambda r: r["entry_time"])
    if any(b["entry_time"] <= a["entry_time"] for a, b in zip(rows, rows[1:])):
        raise ValueError("duplicate time rows")
    return rows


def section(rows, start, end):
    # Purge both feature availability and label ending, including samples that
    # would otherwise cross a validation/test boundary.
    lo, hi = stamp(start), stamp(end)
    return [r for r in rows if r["decision_time"] >= lo and r["exit_time"] < hi]


def percentile(values, p):
    a = sorted(values)
    x = (len(a) - 1) * p
    j = int(x)
    return a[j] + (a[min(j + 1, len(a) - 1)] - a[j]) * (x - j)


def active(row, candidate):
    if candidate["flow"] == "cash":
        return False
    if row["prior_return"] >= 0 or row["rebound"] <= 0 or row["oi_drop"] <= candidate["threshold"]:
        return False
    return candidate["flow"] == "none" or (row["flow"] < 0.5 if candidate["flow"] == "weak" else row["flow"] >= 0.5)


def evaluate_policy(rows, config, cost, start, end):
    days = {}
    day, stop = date.fromisoformat(start), date.fromisoformat(end)
    while day < stop:
        days[day.isoformat()] = 0.0
        day += timedelta(days=1)
    count = 0
    for row in rows:
        if active(row, config):
            key = datetime.fromtimestamp(row["entry_time"] / 1000, timezone.utc).date().isoformat()
            days[key] += -row["forward_return"] + row["funding_short"] - 2 * cost / 10000
            count += 1
    values = list(days.values())
    sd = statistics.stdev(values)
    return {"daily": days, "trades": count, "arithmetic_pnl": sum(values),
            "mean": statistics.mean(values), "sd": sd,
            "selection_score": statistics.mean(values) - 1.645 * sd / math.sqrt(len(values))}


def bootstrap(values, seed, repetitions, block):
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(repetitions):
        total, count = 0.0, 0
        while count < n:
            j = rng.randrange(n)
            take = min(block, n - count)
            total += sum(values[(j + k) % n] for k in range(take))
            count += take
        means.append(total / n)
    return [percentile(means, 0.025), percentile(means, 0.975)]


def run(params, seed):
    rows = read_rows(params)
    folds = []
    net, reference, original = [], [], []
    trades = 0
    high_cost_pnl = 0.0
    for validation_start, test_start, test_end in FOLDS:
        train = section(rows, "2024-07-01", validation_start)
        validation = section(rows, validation_start, test_start)
        test = section(rows, test_start, test_end)
        candidates = [{"flow": "cash", "threshold": 0.0, "quantile": 0.0}]
        for q in params["quantiles"]:
            threshold = percentile([r["oi_drop"] for r in train], q)
            candidates.extend({"flow": flow, "threshold": threshold, "quantile": q}
                              for flow in ("none", "weak", "strong"))
        history = []
        for config in candidates:
            scored = evaluate_policy(validation, config, params["cost_bps"], validation_start, test_start)
            eligible = config["flow"] == "cash" or scored["trades"] >= params["min_validation_trades"]
            history.append({"config": config, "trades": scored["trades"],
                            "score": scored["selection_score"], "eligible": eligible})
        winner = max((r for r in history if r["eligible"]), key=lambda r: r["score"])["config"]
        # Two frozen references: the exploratory OI-only q90 lead and the
        # original full weak-flow q90 rule. Neither is selected on test results.
        q90 = percentile([r["oi_drop"] for r in train], 0.9)
        oi_reference = {"flow": "none", "threshold": q90, "quantile": 0.9}
        weak_reference = {"flow": "weak", "threshold": q90, "quantile": 0.9}
        frozen = {"selected": winner, "history": history, "oi_reference": oi_reference,
                  "weak_reference": weak_reference, "validation_start": validation_start,
                  "test_start": test_start, "test_end": test_end}
        frozen["selection_sha256"] = hashlib.sha256(json.dumps(frozen, sort_keys=True).encode()).hexdigest()
        selected = evaluate_policy(test, winner, params["cost_bps"], test_start, test_end)
        baseline = evaluate_policy(test, oi_reference, params["cost_bps"], test_start, test_end)
        old = evaluate_policy(test, weak_reference, params["cost_bps"], test_start, test_end)
        stress = evaluate_policy(test, winner, params["stress_cost_bps"], test_start, test_end)
        folds.append({"frozen": frozen, "selected": selected, "oi_reference": baseline,
                      "weak_reference": old, "stress_pnl": stress["arithmetic_pnl"]})
        net.extend(selected["daily"].values())
        reference.extend(baseline["daily"].values())
        original.extend(old["daily"].values())
        trades += selected["trades"]
        high_cost_pnl += stress["arithmetic_pnl"]
    delta = [a - b for a, b in zip(net, reference)]
    return {"folds": folds, "trades": trades, "days": len(net),
            "arithmetic_pnl": sum(net), "oi_reference_pnl": sum(reference),
            "weak_reference_pnl": sum(original), "stress_pnl": high_cost_pnl,
            "mean_daily": statistics.mean(net), "mean_delta": statistics.mean(delta),
            "annualized_daily_sharpe": statistics.mean(net) / statistics.stdev(net) * math.sqrt(365) if statistics.stdev(net) else 0.0,
            "positive_interval": bootstrap(net, seed, params["bootstrap_repetitions"], params["block_days"]),
            "delta_interval": bootstrap(delta, seed, params["bootstrap_repetitions"], params["block_days"])}


def evaluate(params, per_seed):
    row = next(iter(per_seed.values()))
    def verdict(bounds):
        if row["trades"] < params["min_test_trades"]:
            return "inconclusive"
        return "supported" if bounds[0] > 0 else "refuted" if bounds[1] < 0 else "inconclusive"
    return {"H1": {"verdict": verdict(row["positive_interval"]),
                   "detail": {"pnl": row["arithmetic_pnl"], "trades": row["trades"], "days": row["days"],
                              "interval": row["positive_interval"], "annualized_daily_sharpe": row["annualized_daily_sharpe"]}},
            "H2": {"verdict": verdict(row["delta_interval"]),
                   "detail": {"mean_incremental_daily": row["mean_delta"], "interval": row["delta_interval"],
                              "oi_reference_pnl": row["oi_reference_pnl"]}},
            "H3": {"verdict": "refuted" if row["trades"] else "inconclusive",
                   "detail": {"base_pnl": row["arithmetic_pnl"], "higher_cost_pnl": row["stress_pnl"]}},
            "H4": {"verdict": "supported" if row["stress_pnl"] > 0 and all(f["selected"]["arithmetic_pnl"] >= 0 for f in row["folds"]) else "refuted",
                   "detail": {"quarterly_pnl": [f["selected"]["arithmetic_pnl"] for f in row["folds"]],
                              "stress_pnl": row["stress_pnl"]}}}


def crosscheck(params, per_seed):
    # Different scalar loop; no calls to active(), section() or evaluate_policy().
    rows = []
    for name in params["sample_files"]:
        with (ROOT / name).open() as stream:
            rows.extend(csv.DictReader(stream))
    stored = next(iter(per_seed.values()))
    checks = []
    for fold in stored["folds"]:
        config = fold["frozen"]["selected"]
        lo, hi = stamp(fold["frozen"]["test_start"]), stamp(fold["frozen"]["test_end"])
        total, count = 0.0, 0
        for row in rows:
            if float(row["decision_time"]) < lo or float(row["exit_time"]) >= hi:
                continue
            if config["flow"] == "cash" or float(row["prior_return"]) >= 0 or float(row["rebound"]) <= 0:
                continue
            if float(row["oi_drop"]) <= config["threshold"]:
                continue
            if config["flow"] == "weak" and float(row["flow"]) >= 0.5:
                continue
            if config["flow"] == "strong" and float(row["flow"]) < 0.5:
                continue
            count += 1
            total += float(row["funding_short"]) - float(row["forward_return"]) - 2 * params["cost_bps"] / 10000
        observed = fold["selected"]
        checks.append({"name": fold["frozen"]["test_start"] + " independent masks and PNL",
                       "observed": observed["arithmetic_pnl"], "reference": total, "tolerance": 1e-10,
                       "ok": abs(observed["arithmetic_pnl"] - total) < 1e-10 and count == observed["trades"]})
    expected = -2 * (params["stress_cost_bps"] - params["cost_bps"]) / 10000 * stored["trades"]
    observed = stored["stress_pnl"] - stored["arithmetic_pnl"]
    checks.append({"name": "fixed-decision cost decrement", "observed": observed,
                   "reference": expected, "tolerance": 1e-10, "ok": abs(expected - observed) < 1e-10})
    return checks
