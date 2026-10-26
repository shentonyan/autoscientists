"""Collect fixed stocks and months for a closer US-minute proxy, without scores."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time

import pyarrow as pa
from equity_public_audit import audit_month, REVISION


def months():
    return [f"{year}-{month:02d}" for year in range(2010, 2026)
            for month in range(1, 13)
            if year != 2020 and not (year == 2025 and month > 7)]


def one(month, output):
    report = output / (month + ".json")
    prices = output / (month + ".parquet")
    if report.exists() and prices.exists():
        record = json.loads(report.read_text())
        if record["revision"] != REVISION or record["filtered_cache_sha256"] != hashlib.sha256(prices.read_bytes()).hexdigest():
            raise ValueError("cached month differs: " + month)
        return record
    last = None
    for attempt in range(3):
        try:
            return audit_month(month, output)
        except (OSError, ValueError) as error:
            last = error
            time.sleep(attempt + 1)
    raise RuntimeError(f"month failed: {month}: {last}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    pa.set_cpu_count(2)
    pa.set_io_thread_count(2)
    reports = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, month, args.output) for month in months()]
        for future in as_completed(futures):
            record = future.result()
            reports.append(record)
            print(json.dumps({"completed_months": len(reports), "planned_months": len(months()), "latest": record["month"]}), flush=True)
    reports.sort(key=lambda r: r["month"])
    (args.output / "collection.json").write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8", newline="\n")
