"""Build causal regular-session panels; no validation/test performance scores."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

SYMBOLS = ("AAPL", "MSFT", "JPM", "XOM")
HISTORY = 64


def feature_grid(grid):
    """grid[:,0:5] = open/high/low/close/volume, one row per regular minute."""
    opening, high, low, close, volume = grid.T
    r1 = np.r_[np.nan, np.log(close[1:] / close[:-1])]
    columns = [np.log(close / opening), r1, np.log(high / low), np.log1p(volume)]
    for lag in (5, 15, 30):
        columns.append(np.r_[np.full(lag, np.nan), np.log(close[lag:] / close[:-lag])])
    vol = np.full(len(grid), np.nan)
    relative = np.full(len(grid), np.nan)
    for i in range(len(grid)):
        if i >= 15 and np.isfinite(r1[i - 14:i + 1]).all():
            vol[i] = np.sqrt(np.mean(r1[i - 14:i + 1] ** 2))
        if i >= 19 and np.isfinite(volume[i - 19:i + 1]).all():
            relative[i] = volume[i] / max(float(volume[i - 19:i + 1].mean()), 1e-12) - 1
    angle = np.arange(len(grid)) / 390 * (2 * np.pi)
    return np.column_stack([*columns, vol, relative, np.sin(angle), np.cos(angle)])


def planned_months():
    return [f"{year}-{month:02d}" for year in range(2010, 2026) for month in range(1, 13)
            if year != 2020 and not (year == 2025 and month > 7)]


def build(cache, output):
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pyarrow.compute as pc
    if output.exists():
        raise ValueError("prepared input output must be a new directory")
    sessions = {name: {} for name in SYMBOLS}
    hashes = {}
    offsets = {}
    zone = ZoneInfo("America/New_York")
    rejected_conflicts = identical_duplicates = invalid_rows = 0
    for month in planned_months():
        filename = month + ".parquet"
        file = cache / filename
        metadata = json.loads((cache / (month + ".json")).read_text())
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
        if actual != metadata["filtered_cache_sha256"]:
            raise ValueError("cached source differs: " + filename)
        hashes[filename] = actual
        table = pq.read_table(file)
        for symbol in SYMBOLS:
            subset = table.filter(pc.equal(table["ticker"], symbol))
            stamps = subset["timestamp"].cast(pa.int64()).to_numpy()
            values = np.column_stack([subset[name].to_numpy() for name in ("open", "high", "low", "close", "volume")])
            days = stamps // 86400000000000
            minutes = stamps // 60000000000
            for day in np.unique(days):
                key = int(day)
                if key not in offsets:
                    noon = datetime.fromtimestamp((key * 86400) + 43200, timezone.utc)
                    offsets[key] = int(noon.astimezone(zone).utcoffset().total_seconds() // 60)
                indices = np.flatnonzero(days == day)
                local = (minutes[indices] + offsets[key]) % 1440
                keep = (local >= 570) & (local < 960)
                indices, local = indices[keep], local[keep] - 570
                if len(indices) == 0:
                    continue
                grid = np.full((390, 5), np.nan)
                groups = defaultdict(list)
                for i, minute in zip(indices, local):
                    groups[int(minute)].append(values[i])
                for minute, observations in groups.items():
                    if any(not np.array_equal(observations[0], other) for other in observations[1:]):
                        rejected_conflicts += 1
                        continue
                    identical_duplicates += len(observations) - 1
                    row = observations[0]
                    o, h, l, c, v = row
                    if not np.isfinite(row).all() or not (0 < l <= min(o, c) <= max(o, c) <= h) or v < 0:
                        invalid_rows += 1
                        continue
                    grid[minute] = row
                sessions[symbol][key] = grid
        print(json.dumps({"prepared_month": month}), flush=True)
    common_days = sorted(set.intersection(*(set(sessions[symbol]) for symbol in SYMBOLS)))
    xs, ys, entries, exits, day_keys = [], [], [], [], []
    for day in common_days:
        grids = [sessions[symbol][day] for symbol in SYMBOLS]
        features = [feature_grid(grid) for grid in grids]
        for i in range(94, 358, 30):
            windows = [f[i - HISTORY + 1:i + 1] for f in features]
            if any(not np.isfinite(w).all() for w in windows):
                continue
            if any(not np.isfinite(grid[[i + 2, i + 32], 0]).all() for grid in grids):
                continue
            xs.append(np.stack(windows).astype(np.float32))
            ys.append([grid[i + 32, 0] / grid[i + 2, 0] - 1 for grid in grids])
            utc_midnight_ms = day * 86400000
            entry = utc_midnight_ms + (570 + i + 2 - offsets[day]) * 60000
            entries.append(entry)
            exits.append(entry + 1800000)
            day_keys.append(day)
    x = np.stack(xs)
    y = np.array(ys, dtype=np.float64)
    entries = np.array(entries, dtype=np.int64)
    exits = np.array(exits, dtype=np.int64)
    dates = np.array(day_keys)
    train_end = int(datetime(2018, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    validation_end = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    test_start = int(datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    split = np.where(entries < train_end, "train", np.where(entries < validation_end, "validation", "test"))
    if np.any((entries >= validation_end) & (entries < test_start)):
        raise ValueError("embargo data unexpectedly present")
    train = split == "train"
    center = x[train].mean(axis=(0, 2), dtype=np.float64)
    scale = np.maximum(x[train].std(axis=(0, 2), dtype=np.float64), 1e-12)
    x = np.clip((x - center[None, :, None, :]) / scale[None, :, None, :], -10, 10).astype(np.float32)
    target_mean = y[train].mean(axis=0)
    target_scale = np.maximum(y[train].std(axis=0), 1e-12)
    output.mkdir(parents=True)
    np.savez_compressed(output / "inputs.npz", x=x, y=y, split=split, entry=entries, exit=exits, day=dates,
                        target_mean=target_mean, target_scale=target_scale)
    metadata = {"symbols": SYMBOLS, "source_revision": "ef1551b11d8ee3e35c7521cf36deee155b43e77d",
                "source_hashes": hashes, "feature_center": center.tolist(), "feature_scale": scale.tolist(),
                "target_mean": target_mean.tolist(), "target_scale": target_scale.tolist(),
                "rows": {s: int(np.sum(split == s)) for s in ("train", "validation", "test")},
                "duplicates_merged": identical_duplicates, "conflicting_minutes_dropped": rejected_conflicts,
                "invalid_minutes_dropped": invalid_rows, "history_minutes": HISTORY,
                "training": "2010-2017", "validation": "2018-2019", "embargo": "2020",
                "testing": "2021 through July 2025, incomplete 2025 calendar year",
                "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "inputs_sha256": hashlib.sha256((output / "inputs.npz").read_bytes()).hexdigest(),
                "scope": "data-only build; no strategy/model scores; source adjustments and survivor-panel limits remain"}
    (output / "quality.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"rows": metadata["rows"], "builder_complete_without_scores": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.cache, args.output)
