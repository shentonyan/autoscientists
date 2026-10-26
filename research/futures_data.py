"""Fetch and causally align public BTC perpetual data; no performance analysis.

Futures quotes are at https://data.binance.vision. Metric records are assumed
available five minutes after their timestamp; this conservative assumption is
not a claim that historical publication latency is known.
"""
import argparse
import bisect
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import time
import urllib.request
import zipfile

BASE = "https://data.binance.vision/data/futures/um"
START = datetime(2024, 7, 1, tzinfo=timezone.utc)
END = datetime(2025, 1, 1, tzinfo=timezone.utc)
STEP = 300000
ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "research/futures_data"


def archive_urls():
    urls = []
    for month in range(7, 13):
        for kind, suffix in (("klines", "5m"), ("fundingRate", None)):
            name = f"BTCUSDT-{suffix or kind}-2024-{month:02d}.zip"
            path = f"monthly/{kind}/BTCUSDT/" + (f"{suffix}/" if suffix else "")
            urls.append(f"{BASE}/{path}{name}")
    day = START
    while day < END:
        name = f"BTCUSDT-metrics-{day:%Y-%m-%d}.zip"
        urls.append(f"{BASE}/daily/metrics/BTCUSDT/{name}")
        day += timedelta(days=1)
    return urls


def fetch_one(pair):
    url, folder = pair
    name = url.rsplit("/", 1)[-1]
    path = folder / name
    checksum = folder / (name + ".CHECKSUM")
    last = None
    for attempt in range(3):
        try:
            if not checksum.exists():
                checksum.write_bytes(urllib.request.urlopen(url + ".CHECKSUM", timeout=40).read())
            expected = checksum.read_text().split()[0]
            blob = path.read_bytes() if path.exists() else urllib.request.urlopen(url, timeout=50).read()
            if hashlib.sha256(blob).hexdigest() != expected:
                raise ValueError(f"checksum differs: {name}")
            if not path.exists():
                path.write_bytes(blob)
            return {"file": name, "url": url, "sha256": expected}
        except (OSError, ValueError) as error:
            last = error
            time.sleep(attempt + 1)
    raise RuntimeError(f"download failed: {name}: {last}")


def fetch(folder):
    raw = folder / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(fetch_one, [(u, raw) for u in archive_urls()]))
    (folder / "provenance.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"archives": len(records), "all_checksums_match": True}))


def read_archive(folder, item):
    blob = (folder / "raw" / item["file"]).read_bytes()
    if hashlib.sha256(blob).hexdigest() != item["sha256"]:
        raise ValueError(f"archive changed: {item['file']}")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if len(z.namelist()) != 1:
            raise ValueError("unexpected archive contents")
        return list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode())))


def load_raw(folder):
    provenance = json.loads((folder / "provenance.json").read_text())
    klines, metrics, funding = [], [], []
    for item in provenance:
        rows = read_archive(folder, item)
        name = item["file"]
        if "-5m-" in name:
            for row in rows:
                klines.append({"time": int(row["open_time"]), "open": float(row["open"]),
                               "close": float(row["close"]), "volume": float(row["volume"]),
                               "buy": float(row["taker_buy_volume"])})
        elif "-metrics-" in name:
            for row in rows:
                stamp = int(datetime.strptime(row["create_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)
                metrics.append({"time": stamp, "oi": float(row["sum_open_interest"])})
        else:
            funding.extend((int(row["calc_time"]), float(row["last_funding_rate"])) for row in rows)
    klines.sort(key=lambda row: row["time"])
    metrics.sort(key=lambda row: row["time"])
    funding.sort()
    if any(not all(math.isfinite(row[key]) for key in ("open", "close", "volume", "buy"))
           or min(row["open"], row["close"]) <= 0 or row["volume"] < 0
           or not 0 <= row["buy"] <= row["volume"] for row in klines):
        raise ValueError("invalid price/volume row")
    if any(not math.isfinite(rate) for _, rate in funding):
        raise ValueError("invalid funding rate")
    for rows in (klines, metrics):
        if any(b["time"] <= a["time"] for a, b in zip(rows, rows[1:])):
            raise ValueError("duplicate or unordered timestamps")
    if any(b["time"] - a["time"] != STEP for a, b in zip(klines, klines[1:])):
        raise ValueError("missing five-minute klines")
    return klines, metrics, funding, provenance


def sample_at(klines, metrics, funding, metric_times, funding_times, i):
    bar = klines[i]
    # At close of bar i, metric timestamp i is assumed published. Any later
    # metric timestamp would have an assumed availability after this close.
    chosen = []
    for index in (i, i - 6, i - 12):
        stamp = klines[index]["time"]
        j = bisect.bisect_right(metric_times, stamp) - 1
        if j < 0 or stamp - metric_times[j] > 2 * STEP:
            return None
        chosen.append(metrics[j])
    if any(m["oi"] <= 0 or not math.isfinite(m["oi"]) for m in chosen):
        return None
    # A full bar of execution latency after the decision is formed.
    entry = klines[i + 2]
    exit_ = klines[i + 8]
    # Exact UTC settlement boundary is rounded down from exchange stamps that
    # sometimes differ by 1ms. Entry-inclusive / exit-exclusive ownership.
    left = bisect.bisect_left(funding_times, entry["time"])
    right = bisect.bisect_left(funding_times, exit_["time"])
    fund = sum(rate for _, rate in funding[left:right])
    recent = klines[i - 5:i + 1]
    total = sum(row["volume"] for row in recent)
    if total <= 0:
        return None
    flow = sum(row["buy"] for row in recent) / total
    if not 0 <= flow <= 1:
        raise ValueError("invalid taker-buy fraction")
    return {"decision_time": bar["time"] + STEP, "entry_time": entry["time"],
            "exit_time": exit_["time"], "metric_time": chosen[0]["time"],
            "oi_drop": max(0, -math.log(chosen[1]["oi"] / chosen[2]["oi"])),
            "prior_return": math.log(klines[i - 6]["close"] / klines[i - 12]["close"]),
            "rebound": math.log(bar["close"] / klines[i - 6]["close"]),
            "flow": flow, "forward_return": exit_["open"] / entry["open"] - 1,
            "funding_short": fund}


def build(folder):
    if (folder / "samples.csv").exists():
        raise ValueError("samples already exist; a new dataset version needs a new directory")
    klines, metrics, funding, provenance = load_raw(folder)
    # Normalizing only funding timestamp jitter, not its realized rate.
    funding = sorted(((stamp // 1000 * 1000, rate) for stamp, rate in funding))
    metric_times = [row["time"] for row in metrics]
    funding_times = [stamp for stamp, _ in funding]
    rows, missing = [], 0
    bounds = [int(datetime(2024, m, 1, tzinfo=timezone.utc).timestamp() * 1000) for m in (7, 9, 10)]
    bounds.append(int(END.timestamp() * 1000))
    for i in range(12, len(klines) - 8, 6):
        sample = sample_at(klines, metrics, funding, metric_times, funding_times, i)
        if sample is None:
            missing += 1
            continue
        for lo, hi, split in zip(bounds, bounds[1:], ("train", "validation", "test")):
            if sample["decision_time"] >= lo and sample["exit_time"] < hi:
                sample["split"] = split
                rows.append(sample)
                break
    path = folder / "samples.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    qa = {"klines": len(klines), "metric_rows": len(metrics), "funding_records": len(funding),
          "metric_missing_or_stale_samples_dropped": missing,
          "split_rows": {s: sum(r["split"] == s for r in rows) for s in ("train", "validation", "test")},
          "samples_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
          "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "provenance_sha256": hashlib.sha256((folder / "provenance.json").read_bytes()).hexdigest(),
          "note": "coverage only; no candidate performance or return summaries inspected"}
    (folder / "quality.json").write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("fetch", "build"))
    parser.add_argument("--data", type=Path, default=DEFAULT)
    args = parser.parse_args()
    (fetch if args.action == "fetch" else build)(args.data)
