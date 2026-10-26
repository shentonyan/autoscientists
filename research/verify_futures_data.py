"""Rebuild pinned inputs and independently audit sampled raw-data alignments."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile

import futures_data as data
from check_futures import audit_raw


def verify(folder=data.DEFAULT):
    quality = json.loads((folder / "quality.json").read_text())
    if hashlib.sha256(Path(data.__file__).read_bytes()).hexdigest() != quality["builder_sha256"]:
        raise ValueError("feature builder differs from the recorded version")
    if hashlib.sha256((folder / "provenance.json").read_bytes()).hexdigest() != quality["provenance_sha256"]:
        raise ValueError("provenance differs from the recorded version")
    audit = audit_raw(folder)
    _, metrics, _, _ = data.load_raw(folder)
    invalid = [row for row in metrics if row["oi"] <= 0 or not math.isfinite(row["oi"])]
    audit["invalid_oi_rows"] = len(invalid)
    audit["invalid_oi_outside_training"] = sum(row["time"] >= 1725148800000 for row in invalid)
    with tempfile.TemporaryDirectory(prefix="futures-rebuild-", dir=data.ROOT.parent) as temp:
        target = Path(temp)
        shutil.copytree(folder / "raw", target / "raw")
        shutil.copyfile(folder / "provenance.json", target / "provenance.json")
        data.build(target)
        actual = hashlib.sha256((target / "samples.csv").read_bytes()).hexdigest()
        if actual != quality["samples_sha256"]:
            raise ValueError("rebuilt samples differ from the pinned CSV")
    audit.update({"rebuilt_samples_match": True, "all_raw_checksums_match": True,
                  "samples_sha256": actual,
                  "scope": "input reconstruction and scalar alignment; not evidence of market efficiency or profitable execution"})
    return audit


if __name__ == "__main__":
    outcome = verify()
    (data.DEFAULT / "raw_audit.json").write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(outcome, indent=2))
