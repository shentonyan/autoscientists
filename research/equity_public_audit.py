"""Schema/coverage-only audit of a public US-minute candidate, no returns scored.

Optional pyarrow/fsspec environment. Source licensing and adjustment provenance
are unresolved; do not redistribute raw/derived prices or claim AQuA equivalence.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import fsspec
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

REPO = "ggaddam/OHLCV-1m"
REVISION = "ef1551b11d8ee3e35c7521cf36deee155b43e77d"
TICKERS = ("AAPL", "MSFT", "JPM", "XOM")


def audit_month(month, output):
    url = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/data/ohlcv_{month}.parquet"
    fs = fsspec.filesystem("http", client_kwargs={"trust_env": True})
    batches = []
    columns = ["timestamp", "open", "high", "low", "close", "volume", "ticker"]
    with fs.open(url, block_size=1024 * 1024, cache_type="bytes") as stream:
        parquet = pq.ParquetFile(stream)
        count = parquet.num_row_groups
        for index in range(count):
            tickers = parquet.read_row_group(index, columns=["ticker"])
            mask = pc.is_in(tickers["ticker"], value_set=pa.array(TICKERS))
            if pc.any(mask).as_py():
                table = parquet.read_row_group(index, columns=columns)
                batches.append(table.filter(mask))
            print(json.dumps({"month": month, "group": index + 1, "groups": count}), flush=True)
    if not batches:
        raise ValueError("no registered stocks found")
    table = pa.concat_tables(batches)
    table = table.sort_by([("ticker", "ascending"), ("timestamp", "ascending")])
    # Local audit cache only; never add prices to the repository.
    path = output / (month + ".parquet")
    pq.write_table(table, path)
    clocks = table["timestamp"].cast(pa.int64()).to_pylist()
    names = table["ticker"].to_pylist()
    opening = table["open"].to_pylist()
    high = table["high"].to_pylist()
    low = table["low"].to_pylist()
    close = table["close"].to_pylist()
    volume = table["volume"].to_pylist()
    stats = {}
    for name in TICKERS:
        ids = [i for i, value in enumerate(names) if value == name]
        times = [clocks[i] for i in ids]
        duplicate = len(times) - len(set(times))
        invalid = sum(not all(math.isfinite(v) for v in (opening[i], high[i], low[i], close[i], volume[i]))
                      or not (0 < low[i] <= min(opening[i], close[i]) <= max(opening[i], close[i]) <= high[i])
                      or volume[i] < 0 for i in ids)
        by_day = Counter(datetime.fromtimestamp(t / 1e9, timezone.utc).date().isoformat() for t in times)
        minute = Counter(datetime.fromtimestamp(t / 1e9, timezone.utc).strftime("%H:%M") for t in times)
        volume_minute = Counter()
        for i in ids:
            key = datetime.fromtimestamp(clocks[i] / 1e9, timezone.utc).strftime("%H:%M")
            volume_minute[key] += volume[i]
        stats[name] = {"rows": len(ids), "days": len(by_day), "duplicates": duplicate,
                       "invalid_ohlcv_rows": invalid,
                       "first_utc": datetime.fromtimestamp(min(times) / 1e9, timezone.utc).isoformat() if times else None,
                       "last_utc": datetime.fromtimestamp(max(times) / 1e9, timezone.utc).isoformat() if times else None,
                       "rows_per_day_min": min(by_day.values()) if by_day else 0,
                       "rows_per_day_max": max(by_day.values()) if by_day else 0,
                       "top_volume_minutes_utc": volume_minute.most_common(8)}
    result = {"repo": REPO, "revision": REVISION, "month": month,
              "schema": str(table.schema), "stocks": stats,
              "filtered_cache_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "source_adjustments": "not independently established", "source_license": "not established by available dataset card",
              "scope": "coverage and consistency only; no model or strategy performance computed"}
    (output / (month + ".json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--month", default="2010-01")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    audit_month(args.month, args.output)
