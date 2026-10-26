"""Replay and independent scalar P&L audit for the crypto pilot.

The scalar audit shares input data and signals with the vectorized backtest.
It independently computes portfolio weights, turnover, liquidation, compounding
and Sharpe. It does not independently validate features or market correctness.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile

import numpy as np
import quant_pilot as q


def scalar_portfolio(panel, signals, cost):
    previous = [0.0] * len(signals)
    net = []
    turnovers = []
    for i in range(len(signals[0])):
        row = [float(s[i]) for s in signals]
        mean = statistics.mean(row)
        centered = [s - mean for s in row]
        denom = max(sum(abs(s) for s in centered), 1e-12)
        weight = [s / denom for s in centered]
        traded = sum(abs(w - old) for w, old in zip(weight, previous))
        pnl = sum(w * float(p["y"][i]) for w, p in zip(weight, panel))
        net.append(pnl - traded * cost / 10000)
        turnovers.append(traded)
        previous = weight
    net[-1] -= cost / 10000 * sum(abs(w) for w in previous)
    equity = 1.0
    peak = 1.0
    drawdown = 0.0
    for r in net:
        equity *= 1 + r
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1)
    return {"net_return": equity - 1,
            "annualized_sharpe": statistics.mean(net) / statistics.stdev(net) * math.sqrt(365 * 48),
            "max_drawdown": drawdown, "mean_turnover": statistics.mean(turnovers)}


def verify(data, output):
    selection = json.loads((output / "selection.json").read_text())
    selected_hash = selection.pop("selection_sha256")
    uses_memory = any("prior_evaluations" in item for item in selection["factor_search"].values())
    assert hashlib.sha256(json.dumps(selection, sort_keys=True, allow_nan=False).encode()).hexdigest() == selected_hash
    metrics = json.loads((output / "metrics.json").read_text())
    assert metrics["selection_sha256"] == selected_hash
    byte_identical = False
    with tempfile.TemporaryDirectory(prefix="aqua-replay-") as temp:
        replay = Path(temp) / "run"
        command = [sys.executable, str(Path(q.__file__)), "run", "--data", str(data.resolve()), "--out", str(replay)]
        if uses_memory:
            memory = Path(temp) / "memory.jsonl"
            memory.write_bytes((output / "memory-before.jsonl").read_bytes())
            command.extend(["--memory", str(memory)])
        subprocess.run(command, check=True, capture_output=True)
        byte_identical = all((output / name).read_bytes() == (replay / name).read_bytes()
                             for name in ("selection.json", "metrics.json"))
        # Git stores LF; Python's default text writer may emit CRLF on Windows.
        # Report byte identity separately instead of treating newline conversion
        # as a numerical failure or silently claiming raw byte identity.
        assert (output / "selection.json").read_text() == (replay / "selection.json").read_text(), "selection replay differs"
        assert (output / "metrics.json").read_text() == (replay / "metrics.json").read_text(), "metrics replay differs"
    panels, records = q.load(data)
    assert records == selection["data"], "data provenance differs from frozen selection"
    splits = q.samples(panels)
    test = splits["test"]
    signal_sets = {}
    for mode, chosen in selection["factor_search"].items():
        scales = [max(float(np.std(q.factor(p["x"], chosen["selected"]))), 1e-12)
                  for p in splits["train"]]
        signal_sets[mode] = [q.factor(p["x"], chosen["selected"]) / scale
                             for p, scale in zip(test, scales)]
    ridge = selection["ridge"]
    signal_sets["ridge"] = [((p["x"] - ridge["center"]) / ridge["scale"]) @ ridge["selected"]["weights"]
                            for p in test]
    checks = []
    for name, signals in signal_sets.items():
        stored = metrics["ridge"] if name == "ridge" else metrics["factors"][name]
        for row in stored:
            reference = scalar_portfolio(test, signals, row["cost_bps_per_one_way_notional"])
            for key, expected in reference.items():
                difference = abs(row[key] - expected)
                if difference > 1e-9:
                    raise AssertionError(f"{name}: {key} differs by {difference}")
                checks.append(difference)
    return {"byte_identical_replay": byte_identical, "newline_normalized_replay": True,
            "independent_scalar_checks": len(checks),
            "max_absolute_difference": max(checks),
            "selection_sha256": selected_hash,
            "scope": "engineering audit; not autosci evidence-level certification or profitability proof"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("research/data"))
    parser.add_argument("--out", type=Path, default=Path("research/results/crypto-v1"))
    args = parser.parse_args()
    result = verify(args.data, args.out)
    print(json.dumps(result, indent=2))
    q.write_json(args.out / "audit.json", result)
