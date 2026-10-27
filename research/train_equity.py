"""Train fixed panel models using training/validation only; export unscored forecasts."""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn

from train_hybrid import Hybrid, setup

CONFIGS = (("cnn32", 32, 0.0), ("cnn32_ic", 32, 0.1),
           ("cnn64_ic", 64, 0.1), ("gru32", 32, 0.0), ("gru32_ic", 32, 0.1))
SEEDS = (7, 19, 43)


class Panel(nn.Module):
    def __init__(self, name, width, features=11, stocks=4):
        super().__init__()
        self.stocks = stocks
        self.recurrent = name.startswith("gru")
        if self.recurrent:
            self.temporal = nn.GRU(features, width, batch_first=True)
        else:
            # Reuse the temporal encoder, replacing its scalar readout.
            self.temporal = Hybrid(features, width)
            self.temporal.head = nn.Identity()
        self.identity = nn.Parameter(torch.zeros(1, stocks, width))
        self.cross = nn.MultiheadAttention(width, 4, dropout=0.1, batch_first=True)
        self.gate = nn.Linear(2 * width, width)
        self.head = nn.Sequential(nn.LayerNorm(width), nn.Linear(width, 1))

    def forward(self, x):
        batch, stocks, history, features = x.shape
        flat = x.reshape(batch * stocks, history, features)
        if self.recurrent:
            z, _ = self.temporal(flat)
            z = z[:, -1]
        else:
            z = self.temporal(flat)
        z = z.reshape(batch, stocks, -1) + self.identity
        other, _ = self.cross(z, z, z, need_weights=False)
        gate = torch.sigmoid(self.gate(torch.cat((z, other), dim=-1)))
        return self.head(z + gate * other).squeeze(-1)


def mean_ic(prediction, target):
    return float(np.mean([np.corrcoef(prediction[:, s], target[:, s])[0, 1]
                          if np.std(prediction[:, s]) and np.std(target[:, s]) else 0.0
                          for s in range(target.shape[1])]))


def ic_loss(prediction, target):
    a = prediction - prediction.mean(0)
    b = target - target.mean(0)
    return -(a.mul(b).sum(0) / (a.square().sum(0) * b.square().sum(0)).clamp_min(1e-12).sqrt()).mean()


@torch.no_grad()
def predict(model, x, device):
    model.eval()
    return np.concatenate([model(torch.from_numpy(x[i:i + 128]).to(device)).cpu().numpy()
                           for i in range(0, len(x), 128)]).astype(np.float64)


def train(name, width, penalty, seed, x, y, split, center, scale, output, device):
    torch.manual_seed(seed)
    model = Panel(name, width).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    train_ids, validation_ids = (np.flatnonzero(split == s) for s in ("train", "validation"))
    rng = np.random.default_rng(seed)
    best, saved, stale, history = -float("inf"), None, 0, []
    for epoch in range(20):
        model.train()
        order = rng.permutation(train_ids)
        losses = []
        for start in range(0, len(order), 128):
            ids = order[start:start + 128]
            target = torch.from_numpy(np.clip((y[ids] - center) / scale, -10, 10).astype(np.float32)).to(device)
            optimizer.zero_grad(set_to_none=True)
            prediction = model(torch.from_numpy(x[ids]).to(device))
            loss = nn.functional.huber_loss(prediction, target) + penalty * ic_loss(prediction, target)
            if not torch.isfinite(loss):
                raise ValueError("nonfinite loss")
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        score = mean_ic(predict(model, x[validation_ids], device), y[validation_ids])
        row = {"epoch": epoch + 1, "loss": float(np.mean(losses)), "validation_ic": score}
        history.append(row)
        print(json.dumps({"model": name, "seed": seed, **row}), flush=True)
        if score > best:
            best, stale = score, 0
            saved = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
        if stale >= 5:
            break
    model.load_state_dict(saved)
    checkpoint = output / f"{name}_{seed}.pt"
    torch.save(saved, checkpoint)
    return predict(model, x, device) * scale + center, {"history": history, "best_validation_ic": best,
            "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest()}


def run(inputs, output, device_name):
    if output.exists():
        raise ValueError("choose a new output directory")
    plan_file = inputs / "plan.json"
    plan = json.loads(plan_file.read_text())
    for key, file in (("trainer_sha256", Path(__file__)), ("inputs_sha256", inputs / "inputs.npz")):
        if plan[key] != hashlib.sha256(file.read_bytes()).hexdigest():
            raise ValueError("pretraining plan mismatch: " + key)
    setup()
    data = np.load(inputs / "inputs.npz", allow_pickle=False)
    x, y, split = (data[k] for k in ("x", "y", "split"))
    center, scale = data["target_mean"], data["target_scale"]
    device = torch.device(device_name)
    output.mkdir(parents=True)
    started = time.monotonic()
    predictions, records = {}, {}
    for name, width, penalty in CONFIGS:
        ensemble = []
        for seed in SEEDS:
            p, receipt = train(name, width, penalty, seed, x, y, split, center, scale, output, device)
            ensemble.append(p)
            records[f"{name}_{seed}"] = receipt
        predictions[name] = np.mean(ensemble, axis=0)
    # Ridge uses the latest observed features and historical means, selected on validation.
    z = np.concatenate((x[:, :, -1], x.mean(2)), axis=-1).astype(np.float64)
    z = np.concatenate((z, np.ones((*z.shape[:2], 1))), axis=-1)
    tr, va = split == "train", split == "validation"
    ridge_candidates = []
    for alpha in (1.0, 100.0, 10000.0):
        p = np.empty_like(y)
        for s in range(4):
            a = z[tr, s]
            beta = np.linalg.solve(a.T @ a + alpha * np.eye(a.shape[1]), a.T @ y[tr, s])
            p[:, s] = z[:, s] @ beta
        ridge_candidates.append((mean_ic(p[va], y[va]), alpha, p))
    score, alpha, predictions["ridge"] = max(ridge_candidates, key=lambda row: row[0])
    records["ridge"] = {"alpha": alpha, "validation_ic": score}
    np.savez_compressed(output / "forecasts.npz", **predictions, y=y, split=split,
                        entry=data["entry"], exit=data["exit"], day=data["day"])
    receipt = {"models": records, "seconds": time.monotonic() - started,
               "plan_sha256": hashlib.sha256(plan_file.read_bytes()).hexdigest(),
               "forecasts_sha256": hashlib.sha256((output / "forecasts.npz").read_bytes()).hexdigest(),
               "test_scores_computed": False}
    (output / "training.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    run(args.inputs, args.output, args.device)
