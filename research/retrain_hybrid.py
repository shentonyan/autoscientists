"""Replay the unchanged trainer into a new directory; preserve pinned forecasts."""
import argparse
import json
from pathlib import Path

import numpy as np
import train_hybrid as trainer


if __name__ == "__main__":
    import csv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("retraining requires a new output directory")
    original = trainer.EXPORT
    trainer.ARTIFACTS = args.output / "weights"
    trainer.EXPORT = args.output / "forecasts"
    trainer.run(args.device)
    with (original / "forecasts.csv").open() as stream:
        before = list(csv.DictReader(stream))
    with (trainer.EXPORT / "forecasts.csv").open() as stream:
        after = list(csv.DictReader(stream))
    if len(before) != len(after) or any(a["entry_time"] != b["entry_time"] for a, b in zip(before, after)):
        raise ValueError("retraining sample order differs")
    differences = {name: max(abs(float(a[name]) - float(b[name])) for a, b in zip(before, after))
                   for name in ("cnn32", "cnn64", "gru32", "ridge")}
    result = {"max_absolute_forecast_differences": differences,
              "within_1e_7": all(value <= 1e-7 for value in differences.values()),
              "scope": "full same-runtime retraining comparison; not cross-hardware guarantee or original AQuA reproduction"}
    (trainer.EXPORT / "retraining_comparison.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))
