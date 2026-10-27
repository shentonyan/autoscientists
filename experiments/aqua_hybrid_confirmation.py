"""Pinned-forecast confirmation; GPU training is separately audited, not L3-certified."""
import csv
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parents[1]


def load(params):
    for name, expected in params["hashes"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError("pinned model dependency changed: " + name)
    with (ROOT / params["forecasts"]).open() as stream:
        rows = list(csv.DictReader(stream))
    output = []
    for row in rows:
        item = {k: float(v) for k, v in row.items() if k != "split"}
        if not all(math.isfinite(v) for v in item.values()):
            raise ValueError("nonfinite forecast")
        item["split"] = row["split"]
        output.append(item)
    return output


def correlation(a, b):
    n = len(a)
    sx, sy = sum(a), sum(b)
    numerator = n * sum(x * y for x, y in zip(a, b)) - sx * sy
    denominator = (n * sum(x * x for x in a) - sx * sx) * (n * sum(y * y for y in b) - sy * sy)
    return numerator / math.sqrt(max(denominator, 1e-60)) if denominator > 0 else 0.0


def quantile(a, p):
    a = sorted(a)
    x = (len(a) - 1) * p
    j = int(x)
    return a[j] + (a[min(j + 1, len(a) - 1)] - a[j]) * (x - j)


def strategy(rows, model, sign, threshold, cost):
    days = {}
    trades = 0
    for r in rows:
        key = datetime.fromtimestamp(r["entry_time"] / 1000, timezone.utc).date().isoformat()
        days.setdefault(key, 0.0)
        signal = sign * r[model]
        position = (1 if signal > 0 else -1) if abs(signal) > threshold else 0
        if position:
            trades += 1
            days[key] += position * (r["forward_return"] - r["funding_short"]) - 2 * cost / 10000
    return {"daily": days, "trades": trades, "pnl": sum(days.values())}


def choose(validation, name, params):
    raw_ic = correlation([r[name] for r in validation], [r["forward_return"] for r in validation])
    sign = 1 if raw_ic >= 0 else -1
    history = []
    for q in params["threshold_quantiles"]:
        cutoff = quantile([abs(r[name]) for r in validation], q)
        result = strategy(validation, name, sign, cutoff, params["cost_bps"])
        history.append({"quantile": q, "cutoff": cutoff, "pnl": result["pnl"], "trades": result["trades"]})
    candidates = [r for r in history if r["trades"] >= params["min_validation_trades"]]
    winner = max(candidates or history, key=lambda r: r["pnl"])
    return {"model": name, "raw_validation_ic": raw_ic, "sign": sign,
            "cutoff": winner["cutoff"], "history": history,
            "abstain": not candidates or winner["pnl"] <= 0}


def bootstrap(test, primary, reference, seed, params):
    by_day = {}
    for r in test:
        key = int(r["entry_time"]) // 86400000
        x = r[primary["model"]] * primary["sign"]
        g = r[reference["model"]] * reference["sign"]
        y = r["forward_return"]
        values = (1, x, g, y, x * x, g * g, y * y, x * y, g * y)
        if key not in by_day:
            by_day[key] = [0.0] * 9
        by_day[key] = [a + b for a, b in zip(by_day[key], values)]
    moments = list(by_day.values())
    def ic(total, index, square, cross):
        n, sy, ssy = total[0], total[3], total[6]
        numerator = n * total[cross] - total[index] * sy
        den = (n * total[square] - total[index] ** 2) * (n * ssy - sy * sy)
        return numerator / math.sqrt(den) if den > 0 else 0.0
    rng = random.Random(seed)
    cis, differences = [], []
    for _ in range(params["bootstrap_repetitions"]):
        total = [0.0] * 9
        count = 0
        while count < len(moments):
            start = rng.randrange(len(moments))
            for j in range(min(params["block_days"], len(moments) - count)):
                value = moments[(start + j) % len(moments)]
                total = [a + b for a, b in zip(total, value)]
                count += 1
        a, b = ic(total, 1, 4, 7), ic(total, 2, 5, 8)
        cis.append(a)
        differences.append(a - b)
    return ([quantile(cis, 0.025), quantile(cis, 0.975)],
            [quantile(differences, 0.025), quantile(differences, 0.975)])


def mean_interval(values, seed, params):
    rng = random.Random(seed)
    means = []
    for _ in range(params["bootstrap_repetitions"]):
        total, count = 0.0, 0
        while count < len(values):
            start = rng.randrange(len(values))
            take = min(params["block_days"], len(values) - count)
            total += sum(values[(start + j) % len(values)] for j in range(take))
            count += take
        means.append(total / len(values))
    return [quantile(means, 0.025), quantile(means, 0.975)]


def run(params, seed):
    rows = load(params)
    validation = [r for r in rows if r["split"] == "validation"]
    test = [r for r in rows if r["split"] == "test"]
    choices = {name: choose(validation, name, params) for name in ("cnn32", "cnn64", "gru32", "ridge")}
    selected = max((choices[name] for name in ("cnn32", "cnn64")), key=lambda r: abs(r["raw_validation_ic"]))
    # Every model, sign and trading threshold above is chosen on validation only.
    outcomes = {}
    for name, choice in choices.items():
        cutoff = float("inf") if choice["abstain"] else choice["cutoff"]
        result = strategy(test, name, choice["sign"], cutoff, params["cost_bps"])
        result["ic"] = correlation([r[name] * choice["sign"] for r in test], [r["forward_return"] for r in test])
        outcomes[name] = result
    primary = outcomes[selected["model"]]
    stress = strategy(test, selected["model"], selected["sign"],
                      float("inf") if selected["abstain"] else selected["cutoff"], params["stress_cost_bps"])
    ic_ci, diff_ci = bootstrap(test, selected, choices["gru32"], seed, params)
    pnl_ci = mean_interval(list(primary["daily"].values()), seed, params)
    values = list(primary["daily"].values())
    sd = statistics.stdev(values)
    return {"selection": selected, "all_choices": choices, "outcomes": outcomes,
            "primary_ic_interval": ic_ci, "ic_vs_gru_interval": diff_ci,
            "pnl_mean_interval": pnl_ci, "stress_pnl": stress["pnl"],
            "days": len(values), "test_rows": len(test),
            "annualized_daily_sharpe": statistics.mean(values) / sd * math.sqrt(365) if sd else 0.0}


def evaluate(params, per_seed):
    r = next(iter(per_seed.values()))
    p = r["outcomes"][r["selection"]["model"]]
    def verdict(bounds):
        return "supported" if bounds[0] > 0 else "refuted" if bounds[1] < 0 else "inconclusive"
    return {"H1": {"verdict": verdict(r["primary_ic_interval"]),
                   "detail": {"selected_model": r["selection"]["model"], "ic": p["ic"], "interval": r["primary_ic_interval"]}},
            "H2": {"verdict": verdict(r["pnl_mean_interval"]) if p["trades"] >= params["min_test_trades"] else "inconclusive",
                   "detail": {"trades": p["trades"], "pnl": p["pnl"], "interval": r["pnl_mean_interval"], "sharpe": r["annualized_daily_sharpe"]}},
            "H3": {"verdict": "refuted" if p["trades"] else "inconclusive",
                   "detail": {"base_pnl": p["pnl"], "higher_cost_pnl": r["stress_pnl"]}},
            "H4": {"verdict": verdict(r["ic_vs_gru_interval"]),
                   "detail": {"gru_ic": r["outcomes"]["gru32"]["ic"], "interval": r["ic_vs_gru_interval"]}}}


def crosscheck(params, per_seed):
    with (ROOT / params["forecasts"]).open() as stream:
        test = [r for r in csv.DictReader(stream) if r["split"] == "test"]
    stored = next(iter(per_seed.values()))
    checks = []
    for name, config in stored["all_choices"].items():
        predictions = [float(r[name]) * config["sign"] for r in test]
        labels = [float(r["forward_return"]) for r in test]
        # Centered covariance reference, not the moment formula used by run().
        mx, my = statistics.mean(predictions), statistics.mean(labels)
        covariance = sum((x - mx) * (y - my) for x, y in zip(predictions, labels))
        denom = math.sqrt(sum((x - mx) ** 2 for x in predictions) * sum((y - my) ** 2 for y in labels))
        reference_ic = covariance / denom if denom else 0
        total, count = 0.0, 0
        for raw in test:
            prediction = float(raw[name]) * config["sign"]
            if not config["abstain"] and abs(prediction) > config["cutoff"]:
                direction = math.copysign(1, prediction)
                total += direction * float(raw["forward_return"]) - direction * float(raw["funding_short"]) - params["cost_bps"] / 5000
                count += 1
        actual = stored["outcomes"][name]
        checks.append({"name": name + " centered Pearson reference and independent trade accounting",
                       "observed": actual["ic"], "reference": reference_ic, "tolerance": 1e-10,
                       "ok": abs(reference_ic - actual["ic"]) < 1e-10 and abs(total - actual["pnl"]) < 1e-10 and count == actual["trades"]})
    return checks
