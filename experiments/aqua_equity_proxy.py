"""Pre-training-locked optional-NumPy evaluation of a fixed US-equity proxy."""
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(params, seed):
    for name, expected in params["hashes"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError("frozen source changed: " + name)
    artifacts = ROOT / params["artifacts"]
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        shutil.copyfile(artifacts / "forecasts.npz", folder / "forecasts.npz")
        subprocess.run([sys.executable, str(ROOT / "research/evaluate_equity.py"),
                        "--directory", str(folder)], check=True, capture_output=True)
        result = json.loads((folder / "evaluation.json").read_text())
    result["training_receipt_sha256"] = hashlib.sha256((artifacts / "training.json").read_bytes()).hexdigest()
    return result


def interval_verdict(interval, eligible=True):
    if not eligible or interval[0] <= 0 <= interval[1]:
        return "inconclusive"
    return "supported" if interval[0] > 0 else "refuted"


def evaluate(params, per_seed):
    result = next(iter(per_seed.values()))
    primary = result["results"][result["chosen_cnn"]]
    active = primary["active_intervals"] >= 100
    return {"H1": {"verdict": interval_verdict(result["primary_ic_ci"]), "detail": result},
            "H2": {"verdict": interval_verdict(result["primary_minus_gru_ic_ci"]),
                   "detail": {"interval": result["primary_minus_gru_ic_ci"]}},
            "H3": {"verdict": interval_verdict(result["mean_daily_pnl_ci"], active),
                   "detail": primary},
            "H4": {"verdict": "inconclusive" if not primary["turnover"] else
                   ("supported" if primary["stress_pnl"] > primary["pnl"] else "refuted"),
                   "detail": {"pnl": primary["pnl"], "stress_pnl": primary["stress_pnl"]}},
            "H5": {"verdict": "supported" if result["joint_proxy_success"] else "refuted",
                   "detail": result["success_components"]}}


def crosscheck(params, per_seed):
    import numpy as np
    data = np.load(ROOT / params["artifacts"] / "forecasts.npz", allow_pickle=False)
    stored = next(iter(per_seed.values()))
    ids = np.flatnonzero(data["split"] == "test")
    checks = []
    for name, choice in stored["validation_selections"].items():
        # Python statistics and scalar cash flows, independent of NumPy evaluator helpers.
        correlations = []
        for stock in range(4):
            p = [float(data[name][i, stock]) * choice["sign"] for i in ids]
            y = [float(data["y"][i, stock]) for i in ids]
            correlations.append(statistics.correlation(p, y) if len(set(p)) > 1 and len(set(y)) > 1 else 0)
        positions = []
        for i in ids:
            p = [float(v) * choice["sign"] for v in data[name][i]]
            position = [0.0] * 4
            if choice["cutoff"] is not None and statistics.pstdev(p) >= choice["cutoff"]:
                order = sorted(range(4), key=lambda j: (p[j], j))
                if p[order[-1]] > p[order[0]]:
                    position[order[0]], position[order[-1]] = -.5, .5
            positions.append(position)
        gross = sum(sum(w * float(r) for w, r in zip(position, data["y"][i]))
                    for i, position in zip(ids, positions))
        # Start with independent round trips, subtract paired netting savings.
        volume = 2 * sum(sum(abs(w) for w in position) for position in positions)
        for k in range(1, len(ids)):
            if data["entry"][ids[k]] == data["exit"][ids[k - 1]]:
                old, new = positions[k - 1], positions[k]
                volume -= sum(abs(a) + abs(b) - abs(a - b) for a, b in zip(old, new))
        actual = stored["results"][name]
        reference_ic, reference_pnl = statistics.mean(correlations), gross - .0001 * volume
        checks.append({"name": name + " scalar centered correlation and round-trip netting",
                       "observed": actual["pnl"], "reference": reference_pnl, "tolerance": 1e-9,
                       "ok": abs(actual["ic"] - reference_ic) < 1e-9 and
                       abs(actual["pnl"] - reference_pnl) < 1e-9 and abs(actual["turnover"] - volume) < 1e-9})
    return checks
