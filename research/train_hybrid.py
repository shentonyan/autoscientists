"""Independent CNN/attention pilot. Train/validate first; never score test here.

Requires the optional torch/NumPy environment. The registered evaluator consumes
pinned forecasts, not a claim of cross-hardware deterministic GPU retraining.
"""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import argparse
import bisect
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
import torch
from torch import nn

import futures_data as base

ROOT = base.ROOT
ARTIFACTS = ROOT / "research/model_artifacts/confirmation"
EXPORT = ROOT / "research/model_forecasts"
HISTORY = 64


def timestamp(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp() * 1000)


def correlation(a, b):
    return float(np.corrcoef(a, b)[0, 1]) if np.std(a) and np.std(b) else 0.0


class Hybrid(nn.Module):
    def __init__(self, inputs, width):
        super().__init__()
        self.conv = nn.Sequential(nn.Conv1d(inputs, width, 3, padding=1), nn.GELU(),
                                  nn.Conv1d(width, width, 7, padding=3), nn.GELU())
        self.position = nn.Parameter(torch.zeros(1, HISTORY, width))
        layer = nn.TransformerEncoderLayer(width, 4, width * 2, dropout=0.1,
                                           batch_first=True, norm_first=True)
        self.attention = nn.TransformerEncoder(layer, 1, enable_nested_tensor=False)
        self.gate = nn.Linear(width * 2, width)
        self.head = nn.Sequential(nn.LayerNorm(width), nn.Linear(width, width), nn.GELU(), nn.Linear(width, 1))

    def forward(self, x):
        z = self.conv(x.transpose(1, 2)).transpose(1, 2) + self.position
        z = self.attention(z)
        last, mean = z[:, -1], z.mean(1)
        gate = torch.sigmoid(self.gate(torch.cat([last, mean], 1)))
        return self.head(gate * last + (1 - gate) * mean).squeeze(-1)


class GRU(nn.Module):
    def __init__(self, inputs):
        super().__init__()
        self.gru = nn.GRU(inputs, 32, batch_first=True)
        self.head = nn.Linear(32, 1)

    def forward(self, x):
        output, _ = self.gru(x)
        return self.head(output[:, -1]).squeeze(-1)


def setup():
    random.seed(20261027)
    np.random.seed(20261027)
    torch.manual_seed(20261027)
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cuda.enable_flash_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(False)
    torch.backends.cuda.enable_math_sdp(True)


def prepare():
    folders = [ROOT / "research/futures_data", ROOT / "research/futures_walk_data", ROOT / "research/futures_model_data"]
    bars, metrics, funding, inputs = [], [], [], {}
    for folder in folders:
        k, m, f, _ = base.load_raw(folder)
        bars.extend(k)
        metrics.extend(m)
        funding.extend(f)
        file = folder / "provenance.json"
        inputs[file.relative_to(ROOT).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    bars.sort(key=lambda r: r["time"])
    metrics.sort(key=lambda r: r["time"])
    funding = sorted((t // 1000 * 1000, r) for t, r in funding)
    times = np.array([b["time"] for b in bars], dtype=np.int64)
    if not np.all(np.diff(times) == base.STEP):
        raise ValueError("non-contiguous market data")
    metric_times = [m["time"] for m in metrics]
    ft = [t for t, _ in funding]
    close = np.array([b["close"] for b in bars])
    opening = np.array([b["open"] for b in bars])
    volume = np.array([b["volume"] for b in bars])
    buy = np.array([b["buy"] for b in bars])
    r = np.r_[0, np.diff(np.log(close))]
    oi = np.full(len(bars), np.nan)
    for i, b in enumerate(bars):
        j = bisect.bisect_right(metric_times, b["time"]) - 1
        if j >= 0 and b["time"] - metric_times[j] <= 2 * base.STEP and metrics[j]["oi"] > 0:
            oi[i] = metrics[j]["oi"]
    oi_change = np.r_[np.nan, np.diff(np.log(oi))]
    momentum = np.r_[np.full(6, np.nan), np.log(close[6:] / close[:-6])]
    squares = np.r_[0, np.cumsum(r * r)]
    volatility = np.r_[np.full(11, np.nan), np.sqrt(np.maximum((squares[12:] - squares[:-12]) / 12, 1e-12))]
    hour = (times // 300000) % 288 / 288 * 2 * np.pi
    features = np.column_stack([np.log(close / opening), r, np.log1p(volume),
                                buy / np.maximum(volume, 1e-12) - 0.5, momentum,
                                volatility, oi_change, np.sin(hour), np.cos(hour)])
    train_bars = times < timestamp("2025-10-01")
    center = np.nanmean(features[train_bars], axis=0)
    scale = np.maximum(np.nanstd(features[train_bars], axis=0), 1e-12)
    normalized = np.clip((features - center) / scale, -10, 10).astype(np.float32)
    indices = []
    splits = []
    labels = []
    funding_labels = []
    entry_times = []
    for i in range(66, len(bars) - 8, 6):
        if not np.isfinite(normalized[i - HISTORY + 1:i + 1]).all():
            continue
        decision, entry, exit_ = times[i] + base.STEP, times[i + 2], times[i + 8]
        split = None
        for name, lo, hi in (("train", "2024-07-01", "2025-10-01"),
                             ("validation", "2025-10-01", "2026-01-01"),
                             ("test", "2026-01-01", "2026-10-01")):
            if decision >= timestamp(lo) and exit_ < timestamp(hi):
                split = name
                break
        if split is None:
            continue
        indices.append(i)
        splits.append(split)
        labels.append(opening[i + 8] / opening[i + 2] - 1)
        left, right = bisect.bisect_left(ft, entry), bisect.bisect_left(ft, exit_)
        funding_labels.append(sum(rate for _, rate in funding[left:right]))
        entry_times.append(entry)
    windows = np.lib.stride_tricks.sliding_window_view(normalized, HISTORY, axis=0)
    x = windows[np.array(indices) - HISTORY + 1].transpose(0, 2, 1).copy()
    y = np.array(labels, dtype=np.float64)
    split = np.array(splits)
    metadata = {"inputs": inputs, "feature_center": center.tolist(), "feature_scale": scale.tolist(),
                "feature_names": ["close_open", "return_1", "log_volume", "taker_buy_fraction", "momentum_6", "volatility_12", "oi_change", "time_sin", "time_cos"],
                "rows": {key: int(np.sum(split == key)) for key in ("train", "validation", "test")}}
    return x, y, split, np.array(entry_times), np.array(funding_labels), metadata


@torch.no_grad()
def predict(model, x, device):
    model.eval()
    result = []
    for start in range(0, len(x), 512):
        tensor = torch.from_numpy(x[start:start + 512]).to(device)
        result.append(model(tensor).float().cpu().numpy())
    return np.concatenate(result).astype(np.float64)


def train_one(name, x, y, split, device, target_scale, seed):
    torch.manual_seed(seed)
    architecture = name.split("_")[0]
    model = GRU(x.shape[2]) if architecture == "gru32" else Hybrid(x.shape[2], 32 if architecture == "cnn32" else 64)
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    train_ids = np.flatnonzero(split == "train")
    val_ids = np.flatnonzero(split == "validation")
    generator = np.random.default_rng(seed)
    best, best_state, stale = -float("inf"), None, 0
    history = []
    start = time.monotonic()
    for epoch in range(16):
        model.train()
        losses = []
        for offset in range(0, len(train_ids), 256):
            if offset == 0:
                shuffled = generator.permutation(train_ids)
            ids = shuffled[offset:offset + 256]
            batch = torch.from_numpy(x[ids]).to(device)
            target = torch.from_numpy(np.clip(y[ids] / target_scale, -10, 10).astype(np.float32)).to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.huber_loss(model(batch), target, delta=1.0)
            if not torch.isfinite(loss):
                raise ValueError("nonfinite training loss")
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        validation_prediction = predict(model, x[val_ids], device)
        score = correlation(validation_prediction, y[val_ids])
        history.append({"epoch": epoch + 1, "train_loss": float(np.mean(losses)), "validation_ic": score})
        if score > best:
            best = score
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
        print(json.dumps({"model": name, **history[-1]}), flush=True)
        if stale >= 4:
            break
    model.load_state_dict(best_state)
    torch.save(best_state, ARTIFACTS / (name + ".pt"))
    prediction = predict(model, x, device) * target_scale
    return prediction, {"history": history, "best_validation_ic": best,
                        "seconds": time.monotonic() - start,
                        "checkpoint_sha256": hashlib.sha256((ARTIFACTS / (name + ".pt")).read_bytes()).hexdigest()}


def run(device_name):
    if ARTIFACTS.exists() or (EXPORT / "forecasts.csv").exists():
        raise ValueError("immutable artifacts already exist; use a new versioned trainer")
    setup()
    device = torch.device(device_name)
    # Task-specific forward/backward/optimizer smoke, before data/training.
    smoke = Hybrid(9, 32).to(device)
    optimizer = torch.optim.AdamW(smoke.parameters())
    loss = smoke(torch.randn(4, HISTORY, 9, device=device)).square().mean()
    loss.backward()
    optimizer.step()
    if not torch.isfinite(loss):
        raise ValueError("hybrid smoke failed")
    del smoke, optimizer
    x, y, split, times, funding, metadata = prepare()
    ARTIFACTS.mkdir(parents=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ARTIFACTS / "inputs.npz", x=x, y=y, split=split, times=times, funding=funding)
    train = split == "train"
    val = split == "validation"
    target_scale = max(float(np.std(y[train])), 1e-12)
    metadata.update({"trainer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     "torch": torch.__version__, "numpy": np.__version__, "history": HISTORY,
                     "target_scale": target_scale, "models": {},
                     "scope": "independent BTC model development; test performance not computed by trainer"})
    forecasts = {}
    for name in ("cnn32", "cnn64", "gru32"):
        members, records = [], []
        for seed in (7, 19, 43):
            prediction, training = train_one(name + "_s" + str(seed), x, y, split, device, target_scale, seed)
            members.append(prediction)
            records.append({"seed": seed, **training})
        forecasts[name] = np.mean(members, axis=0)
        metadata["models"][name] = {"members": records, "ensemble_validation_ic": correlation(forecasts[name][val], y[val])}
    features = np.concatenate([x[:, -1], x.mean(1)], axis=1).astype(np.float64)
    design = np.column_stack([np.ones(len(x)), features])
    penalty = np.eye(design.shape[1])
    penalty[0, 0] = 0
    weights = np.linalg.solve(design[train].T @ design[train] + penalty, design[train].T @ y[train])
    forecasts["ridge"] = design @ weights
    metadata["models"]["ridge"] = {"weights": weights.tolist(), "validation_ic": correlation(forecasts["ridge"][val], y[val])}
    # Export raw predictions and labels without scoring the held-out window.
    with (EXPORT / "forecasts.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["entry_time", "split", "forward_return", "funding_short", *forecasts])
        for i in range(len(y)):
            if split[i] != "train":
                writer.writerow([int(times[i]), split[i], repr(float(y[i])), repr(float(funding[i])),
                                 *(repr(float(forecasts[name][i])) for name in forecasts)])
    metadata["forecasts_sha256"] = hashlib.sha256((EXPORT / "forecasts.csv").read_bytes()).hexdigest()
    if device.type == "cuda":
        metadata["peak_allocated_bytes"] = int(torch.cuda.max_memory_allocated())
    (EXPORT / "training.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"rows": metadata["rows"], "export_complete_without_test_scores": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    run(args.device)
