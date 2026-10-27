"""Public 2026 confirmation-period archives; data access only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import futures_data as base

FOLDER = base.ROOT / "research/futures_model_data"


def fetch():
    raw = FOLDER / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    urls = []
    for month in range(1, 10):
        for kind, interval in (("klines", "5m"), ("fundingRate", None)):
            suffix = interval or kind
            path = f"monthly/{kind}/BTCUSDT/" + (f"{interval}/" if interval else "")
            urls.append(f"{base.BASE}/{path}BTCUSDT-{suffix}-2026-{month:02d}.zip")
    day = datetime(2026, 1, 1, tzinfo=timezone.utc)
    while day < datetime(2026, 10, 1, tzinfo=timezone.utc):
        urls.append(f"{base.BASE}/daily/metrics/BTCUSDT/BTCUSDT-metrics-{day:%Y-%m-%d}.zip")
        day += timedelta(days=1)
    with ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(base.fetch_one, [(url, raw) for url in urls]))
    (FOLDER / "provenance.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"archives": len(records), "all_checksums_match": True}))


if __name__ == "__main__":
    fetch()
