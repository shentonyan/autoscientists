"""Rebuild 2025 inputs and independently sample raw alignments."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import futures_data as base
import futures_walk_data as walk
from check_futures import audit_raw


def verify():
    folder = walk.FOLDER
    quality = json.loads((folder / "quality.json").read_text())
    for file, key in ((Path(walk.__file__), "builder_sha256"), (Path(base.__file__), "base_builder_sha256"),
                      (folder / "provenance.json", "provenance_sha256")):
        if hashlib.sha256(file.read_bytes()).hexdigest() != quality[key]:
            raise ValueError("recorded dependency changed: " + file.name)
    result = audit_raw(folder)
    with tempfile.TemporaryDirectory(prefix="walk-rebuild-", dir=base.ROOT.parent) as temp:
        target = Path(temp)
        shutil.copytree(folder / "raw", target / "raw")
        shutil.copyfile(folder / "provenance.json", target / "provenance.json")
        walk.build(target)
        actual = hashlib.sha256((target / "samples.csv").read_bytes()).hexdigest()
        if actual != quality["samples_sha256"]:
            raise ValueError("reconstructed input differs")
    result.update({"all_archive_checksums_match": True, "rebuilt_samples_match": True,
                   "samples_sha256": actual})
    return result


if __name__ == "__main__":
    outcome = verify()
    (walk.FOLDER / "raw_audit.json").write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(outcome, indent=2))
