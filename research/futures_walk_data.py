"""2025 data-only extension; no candidate scores or holdout return summaries."""
import argparse
import bisect
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import csv
import hashlib
import json
from pathlib import Path

import futures_data as base

FOLDER = base.ROOT / "research/futures_walk_data"


def fetch(folder):
    raw = folder / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    urls = []
    for month in range(1, 13):
        for kind, interval in (("klines", "5m"), ("fundingRate", None)):
            suffix = interval or kind
            path = f"monthly/{kind}/BTCUSDT/" + (f"{interval}/" if interval else "")
            urls.append(f"{base.BASE}/{path}BTCUSDT-{suffix}-2025-{month:02d}.zip")
    day = datetime(2025, 1, 1, tzinfo=timezone.utc)
    while day.year == 2025:
        urls.append(f"{base.BASE}/daily/metrics/BTCUSDT/BTCUSDT-metrics-{day:%Y-%m-%d}.zip")
        day += timedelta(days=1)
    with ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(base.fetch_one, [(u, raw) for u in urls]))
    (folder / "provenance.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"archives": len(records), "all_checksums_match": True}))


def build(folder):
    target = folder / "samples.csv"
    if target.exists():
        raise ValueError("existing samples are immutable; use a new directory")
    bars, metrics, funding, _ = base.load_raw(folder)
    clocks = [m["time"] for m in metrics]
    funding = sorted((t // 1000 * 1000, r) for t, r in funding)
    funding_clocks = [t for t, _ in funding]
    rows = []
    dropped = 0
    for i in range(12, len(bars) - 8, 6):
        row = base.sample_at(bars, metrics, funding, clocks, funding_clocks, i)
        if row is None:
            dropped += 1
            continue
        row["split"] = "walk_forward"
        rows.append(row)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    quality = {"rows": len(rows), "klines": len(bars), "metric_rows": len(metrics),
               "funding_records": len(funding), "dropped_invalid_or_stale": dropped,
               "samples_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
               "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "base_builder_sha256": hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest(),
               "provenance_sha256": hashlib.sha256((folder / "provenance.json").read_bytes()).hexdigest(),
               "note": "input coverage only; no candidate or holdout performance computed"}
    (folder / "quality.json").write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("fetch", "build"))
    parser.add_argument("--data", type=Path, default=FOLDER)
    args = parser.parse_args()
    (fetch if args.action == "fetch" else build)(args.data)
