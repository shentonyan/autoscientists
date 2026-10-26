"""AQuA-inspired public-data pilot, NOT a replication of its undisclosed signals.

Run directly with an explicit Python interpreter and NumPy. The core autosci
package remains standard-library-only. No exchange account or API key is used.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import urllib.request
import zipfile

import numpy as np
from research_memory import ResearchMemory

SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT")
MONTHS = tuple(f"2024-{m:02d}" for m in range(1, 7))
BASE = "https://data.binance.vision/data/spot/monthly/klines"
HORIZON = 6  # six five-minute bars; predict next-open to open 30m later
WINDOWS = (3, 6, 12, 24, 48, 96)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def fetch(data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for symbol in SYMBOLS:
        for month in MONTHS:
            name = f"{symbol}-5m-{month}.zip"
            url = f"{BASE}/{symbol}/5m/{name}"
            path = data_dir / name
            check_path = data_dir / (name + ".CHECKSUM")
            if not check_path.exists():
                check_path.write_bytes(urllib.request.urlopen(url + ".CHECKSUM", timeout=45).read())
            expected = check_path.read_text().split()[0]
            if not path.exists():
                blob = urllib.request.urlopen(url, timeout=60).read()
                if hashlib.sha256(blob).hexdigest() != expected:
                    raise ValueError(f"upstream checksum mismatch: {name}")
                path.write_bytes(blob)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f"local checksum mismatch: {name}")
            records.append({"file": name, "url": url, "sha256": actual})
    write_json(data_dir / "provenance.json", records)
    return records


def load(data_dir):
    records = json.loads((data_dir / "provenance.json").read_text())
    mapping = {r["file"]: r for r in records}
    panels = {}
    for symbol in SYMBOLS:
        rows = []
        for month in MONTHS:
            name = f"{symbol}-5m-{month}.zip"
            blob = (data_dir / name).read_bytes()
            if hashlib.sha256(blob).hexdigest() != mapping[name]["sha256"]:
                raise ValueError(f"data changed: {name}")
            with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                names = archive.namelist()
                if len(names) != 1:
                    raise ValueError("unexpected archive layout")
                text = archive.read(names[0]).decode()
                for row in csv.reader(io.StringIO(text)):
                    rows.append([int(row[0]), float(row[1]), float(row[4]), float(row[5])])
        a = np.array(rows, dtype=float)
        if not np.isfinite(a).all() or np.any(a[:, 1:3] <= 0) or np.any(a[:, 3] < 0):
            raise ValueError("invalid market data")
        if not np.all(np.diff(a[:, 0]) == 300000):
            raise ValueError("duplicate, unordered or missing five-minute bars")
        panels[symbol] = a
    clocks = [a[:, 0] for a in panels.values()]
    if not all(np.array_equal(clocks[0], clock) for clock in clocks[1:]):
        raise ValueError("asset timestamps do not align")
    return panels, records


def trailing(x, w):
    """Mean including the current, already closed bar; never a forward window."""
    sums = np.r_[0.0, np.cumsum(x)]
    out = np.full(len(x), np.nan)
    out[w - 1:] = (sums[w:] - sums[:-w]) / w
    return out


def features(a):
    close, volume = a[:, 2], a[:, 3]
    ret = np.r_[0.0, np.diff(np.log(close))]
    vol = np.sqrt(np.maximum(trailing(ret * ret, 48) - trailing(ret, 48) ** 2, 1e-12))
    volume_mean = trailing(volume, 48)
    vz = volume / np.maximum(volume_mean, 1e-12) - 1
    columns = []
    for window in WINDOWS:
        momentum = np.full(len(a), np.nan)
        momentum[window:] = np.log(close[window:] / close[:-window])
        columns.extend((momentum, momentum / vol, momentum * np.clip(vz, -1, 5)))
    return np.column_stack(columns)


def validate_candidate(spec):
    if not isinstance(spec, dict) or set(spec) != {"kind", "window", "sign"}:
        raise ValueError("candidate keys must be kind, window and sign")
    if type(spec["window"]) is not int or spec["window"] not in WINDOWS:
        raise ValueError("unregistered window")
    if type(spec["sign"]) is not int or spec["sign"] not in (-1, 1):
        raise ValueError("invalid sign")
    if spec["kind"] not in ("momentum", "risk_scaled", "volume_conditioned"):
        raise ValueError("unregistered kind")
    return spec


def factor(x, spec):
    validate_candidate(spec)
    offset = ("momentum", "risk_scaled", "volume_conditioned").index(spec["kind"])
    return spec["sign"] * x[:, WINDOWS.index(spec["window"]) * 3 + offset]


def ranks(a):
    # Average tied ranks, rather than silently imposing an arbitrary tie order.
    order = np.argsort(a, kind="stable")
    sorted_a = a[order]
    starts = np.r_[0, np.flatnonzero(np.diff(sorted_a)) + 1]
    ends = np.r_[starts[1:], len(a)]
    result = np.empty(len(a), dtype=float)
    for start, end in zip(starts, ends):
        result[order[start:end]] = (start + end - 1) / 2
    return result


def corr(a, b):
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def ic(panel, signals):
    return float(np.mean([corr(ranks(s), ranks(panel[i]["y"])) for i, s in enumerate(signals)]))


def samples(panels):
    result = {"train": [], "validation": [], "test": []}
    # UTC boundaries are chosen in source before any market results are examined.
    edges = (1704067200000, 1711929600000, 1714521600000, 1719792000000)
    for symbol, a in panels.items():
        x = features(a)
        # Adjacent positions hold disjoint 30m open-to-open returns.
        t = np.arange(96, len(a) - HORIZON - 1, HORIZON)
        entry, exit_ = t + 1, t + 1 + HORIZON
        y = a[exit_, 1] / a[entry, 1] - 1
        for j, key in enumerate(result):
            # Both feature availability and the label end must lie in split.
            keep = (a[t, 0] >= edges[j]) & (a[exit_, 0] < edges[j + 1])
            result[key].append({"symbol": symbol, "x": x[t[keep]], "y": y[keep],
                                "time": a[entry[keep], 0].astype(np.int64)})
    return result


def select_factor(validation, mode, seed, budget, memory=None):
    registry = [{"kind": k, "window": w, "sign": s}
                for k in ("momentum", "risk_scaled", "volume_conditioned")
                for w in WINDOWS for s in (-1, 1)]
    rng = np.random.default_rng(seed)
    unseen = list(range(len(registry)))
    history = []
    priors = []
    if memory is not None:
        priors = [{"candidate": row["candidate"], "validation_ic": row["validation_score"]}
                  for row in memory.rows]
        unseen = [i for i in unseen if not any(registry[i] == row["candidate"] for row in priors)]
        if budget > len(unseen):
            raise ValueError("search registry exhausted: reduce new-evaluation budget or start a separately declared search")
    for step in range(budget):
        if mode == "memory" and (step >= 4 or priors):
            best = max(priors + history, key=lambda row: row["validation_ic"])["candidate"]
            # Search the nearest unexplored registered neighbor of the best.
            def distance(i):
                c = registry[i]
                return (2 * (c["kind"] != best["kind"]) + 3 * (c["sign"] != best["sign"])
                        + abs(WINDOWS.index(c["window"]) - WINDOWS.index(best["window"])))
            distances = [distance(i) for i in unseen]
            choices = [i for i, d in zip(unseen, distances) if d == min(distances)]
            index = int(rng.choice(choices))
        else:
            index = int(rng.choice(unseen))
        unseen.remove(index)
        c = registry[index]
        score = ic(validation, [factor(p["x"], c) for p in validation])
        history.append({"candidate": c, "validation_ic": score})
        if memory is not None:
            memory.append(c, score)
    winner = max(priors + history, key=lambda row: row["validation_ic"])
    result = {"selected": winner["candidate"], "history": history, "budget": budget}
    if memory is not None:
        result["prior_evaluations"] = len(priors)
        result["memory_head"] = memory.head
    return result


def fit_ridge(train, validation):
    x = np.concatenate([p["x"] for p in train])
    y = np.concatenate([p["y"] for p in train])
    center, scale = x.mean(axis=0), np.maximum(x.std(axis=0), 1e-12)
    z = (x - center) / scale
    target_mean = float(y.mean())
    history = []
    for penalty in (0.01, 0.1, 1.0, 10.0, 100.0):
        weight = np.linalg.solve(z.T @ z + penalty * np.eye(z.shape[1]), z.T @ (y - target_mean))
        score = ic(validation, [((p["x"] - center) / scale) @ weight for p in validation])
        history.append({"penalty": penalty, "validation_ic": score, "weights": weight.tolist()})
    winner = max(history, key=lambda row: row["validation_ic"])
    return {"center": center.tolist(), "scale": scale.tolist(), "target_mean": target_mean,
            "selected": winner, "history": history}


def portfolio(panel, signals, cost_bps):
    # Dollar-neutral cross-asset book. Uniform gross exposure 1, rebalance 30m.
    scores = np.column_stack(signals)
    centered = scores - scores.mean(axis=1, keepdims=True)
    weights = centered / np.maximum(np.abs(centered).sum(axis=1, keepdims=True), 1e-12)
    returns = np.column_stack([p["y"] for p in panel])
    gross = (weights * returns).sum(axis=1)
    turnover = np.abs(np.diff(np.vstack([np.zeros((1, weights.shape[1])), weights]), axis=0)).sum(axis=1)
    net = gross - cost_bps / 10000 * turnover
    # Liquidate the final book, so a constant position pays entry AND exit costs.
    net[-1] -= cost_bps / 10000 * np.abs(weights[-1]).sum()
    annual = math.sqrt(365 * 48)
    sharpe = float(net.mean() / net.std(ddof=1) * annual) if np.std(net) else 0.0
    equity = np.cumprod(1 + net)
    peak = np.maximum.accumulate(np.r_[1.0, equity])[1:]
    return {"cost_bps_per_one_way_notional": cost_bps, "annualized_sharpe": sharpe,
            "net_return": float(equity[-1] - 1), "max_drawdown": float(np.min(equity / peak - 1)),
            "periods": len(net), "mean_turnover": float(turnover.mean()),
            "ic": ic(panel, signals)}


def run(data_dir, out, memory_path=None):
    if out.exists():
        raise ValueError("output already exists: use a new run directory")
    panels, provenance = load(data_dir)
    splits = samples(panels)
    out.mkdir(parents=True)
    memory = None
    if memory_path is not None:
        # Scope includes the implementation and train/validation inputs, never
        # test metrics. Changing the research contract requires a new memory.
        scope = digest({"data": [r for r in provenance if any(f"-{month}." in r["file"] for month in MONTHS[:4])],
                        "code": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        "memory_code": hashlib.sha256(Path(__file__).with_name("research_memory.py").read_bytes()).hexdigest(),
                        "objective": "mean per-asset validation Spearman IC", "windows": WINDOWS})
        memory = ResearchMemory(memory_path, scope, validate_candidate)
        # Preserve the exact pre-run ledger so this run can be replayed even
        # after the live memory grows. This is validation history, not test data.
        (out / "memory-before.jsonl").write_text(
            memory.path.read_text(encoding="utf-8") if memory.path.exists() else "", encoding="utf-8")
    selected = {mode: select_factor(splits["validation"], mode, 20261026, 12,
                                    memory if mode == "memory" else None)
                for mode in ("random", "no_memory", "memory")}
    # no_memory is explicitly the same IID-without-replacement control.
    ridge = fit_ridge(splits["train"], splits["validation"])
    frozen = {"scope": "independent crypto pilot; not the paper's result",
              "data": provenance, "symbols": SYMBOLS, "months": MONTHS,
              "split": {"train": "2024-01 through 2024-03", "validation": "2024-04", "test": "2024-05 through 2024-06"},
              "horizon_bars": HORIZON, "seed": 20261026,
              "factor_search": selected, "ridge": ridge, "numpy": np.__version__,
              "cost_convention": "1bp one-way per traded notional; 2bp round trip on unchanged unit exposure",
              "limitations": ["spot data with hypothetical shorts; borrow, funding and slippage omitted",
                              "application-level test separation; not an OS access-control boundary",
                              "single seed and short test period do not establish memory improvement",
                              "no LLM proposal calls or undisclosed AQuA model architecture"]}
    # Persist and hash the full selected configuration before scoring any test.
    frozen["selection_sha256"] = digest(frozen)
    write_json(out / "selection.json", frozen)
    test = splits["test"]
    report = {"selection_sha256": frozen["selection_sha256"], "factors": {}}
    for mode, selection in selected.items():
        signals = [factor(p["x"], selection["selected"]) for p in test]
        # Use train-only per-asset scale to compare heterogeneous factor units.
        scale = [max(float(np.std(factor(p["x"], selection["selected"]))), 1e-12)
                 for p in splits["train"]]
        signals = [s / d for s, d in zip(signals, scale)]
        report["factors"][mode] = [portfolio(test, signals, cost) for cost in (0, 1, 2, 5)]
    weights = np.array(ridge["selected"]["weights"])
    prediction = [((p["x"] - ridge["center"]) / ridge["scale"]) @ weights for p in test]
    report["ridge"] = [portfolio(test, prediction, cost) for cost in (0, 1, 2, 5)]
    report["rows"] = {key: {p["symbol"]: len(p["y"]) for p in part} for key, part in splits.items()}
    report["no_memory_equals_random"] = selected["no_memory"] == selected["random"]
    write_json(out / "metrics.json", report)
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("fetch", "run"))
    parser.add_argument("--data", type=Path, default=Path("research/data"))
    parser.add_argument("--out", type=Path, default=Path("research/results/crypto-v1"))
    parser.add_argument("--memory", type=Path, help="optional validation-only memory; carried budgets must be reported")
    args = parser.parse_args()
    if args.action == "fetch":
        print(json.dumps(fetch(args.data), indent=2))
    else:
        run(args.data, args.out, args.memory)


if __name__ == "__main__":
    main()
