"""Checkpoint inference replay and input reconstruction, not a retraining proof."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
import train_hybrid as trainer


def audit():
    trainer.setup()
    metadata = json.loads((trainer.EXPORT / "training.json").read_text())
    if hashlib.sha256(Path(trainer.__file__).read_bytes()).hexdigest() != metadata["trainer_sha256"]:
        raise ValueError("frozen trainer changed")
    data = np.load(trainer.ARTIFACTS / "inputs.npz")
    x, y, splits, times, funding, rebuilt = trainer.prepare()
    for name, expected in (("x", x), ("y", y), ("split", splits), ("times", times), ("funding", funding)):
        if not np.array_equal(data[name], expected):
            raise ValueError("raw reconstruction differs: " + name)
    if metadata["inputs"] != rebuilt["inputs"]:
        raise ValueError("raw provenance differs")
    with (trainer.EXPORT / "forecasts.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    mask = splits != "train"
    if [int(r["entry_time"]) for r in rows] != times[mask].tolist():
        raise ValueError("forecast timestamps differ")
    differences = {}
    device = torch.device("cuda")
    for name in ("cnn32", "cnn64", "gru32"):
        predictions = []
        for member in metadata["models"][name]["members"]:
            file = trainer.ARTIFACTS / f"{name}_s{member['seed']}.pt"
            if hashlib.sha256(file.read_bytes()).hexdigest() != member["checkpoint_sha256"]:
                raise ValueError("checkpoint differs")
            model = trainer.GRU(x.shape[2]) if name == "gru32" else trainer.Hybrid(x.shape[2], 32 if name == "cnn32" else 64)
            model.load_state_dict(torch.load(file, map_location="cpu", weights_only=True))
            model.to(device)
            predictions.append(trainer.predict(model, x[mask], device) * metadata["target_scale"])
        replay = np.mean(predictions, axis=0)
        recorded = np.array([float(row[name]) for row in rows])
        differences[name] = float(np.max(np.abs(replay - recorded)))
        if differences[name] > 1e-7:
            raise ValueError("inference replay differs: " + name)
    features = np.concatenate([x[:, -1], x.mean(1)], axis=1).astype(np.float64)
    ridge = np.column_stack([np.ones(len(x)), features]) @ metadata["models"]["ridge"]["weights"]
    differences["ridge"] = float(np.max(np.abs(ridge[mask] - np.array([float(r["ridge"]) for r in rows]))))
    if differences["ridge"] > 1e-10:
        raise ValueError("ridge replay differs")
    if not np.array_equal(np.array([float(r["forward_return"]) for r in rows]), y[mask]):
        raise ValueError("exported labels differ")
    outcome = {"raw_inputs_rebuilt_identically": True, "checkpoint_inference_replay_passed": True,
               "max_absolute_prediction_differences": differences,
               "scope": "same forward model, raw preparation and checkpoint replay; not independent architecture validation or full training replay"}
    (trainer.EXPORT / "inference_audit.json").write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(outcome, indent=2))


if __name__ == "__main__":
    audit()
