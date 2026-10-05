"""Guard: the frozen core and who may change it.

`state/protected.json` lists glob patterns for the files that make up the
verifier and the rules (the framework code, the calibration card and experiment,
the tests, the protocol, the governor limits) with the sha256 of each.

Two checks:

* default: the working tree against the manifest in the working tree. Catches
  edits made without updating the manifest, and new files under a protected
  pattern.
* `--base REF`: the working tree against the manifest as it stood on REF
  (normally the branch the maintainer has already approved). Any difference is a
  change to the frozen core and is reported as needing the maintainer's
  approval. This is the check that matters for a proposed self-modification: the
  loop can propose such a change, but it cannot make it pass quietly.

`--update` rewrites the manifest from the current files. It is a convenience for
the maintainer; the diff of the manifest is part of what they review.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .canon import sha256_file
from .paths import Layout

DEFAULT_PATTERNS = [
    "autosci/*.py",
    "experiments/auction_calibration.py",
    "cards/auction-calibration.json",
    "cards/auction-calibration.lock.json",
    "tests/*.py",
    "PROTOCOL.md",
    "docs/EVOLUTION.md",
    "state/governor.json",
]


def _expand(layout: Layout, patterns: list[str]) -> dict[str, str]:
    files: dict[str, str] = {}
    for pat in patterns:
        for p in sorted(layout.root.glob(pat)):
            if p.is_file():
                files[p.relative_to(layout.root).as_posix()] = sha256_file(p)
    return files


def build_manifest(layout: Layout, patterns: list[str] | None = None) -> dict:
    pats = patterns if patterns is not None else DEFAULT_PATTERNS
    return {"patterns": list(pats), "files": _expand(layout, pats)}


def update(layout: Layout) -> dict:
    patterns = None
    if layout.protected.exists():
        patterns = json.loads(layout.protected.read_text(encoding="utf-8"))["patterns"]
    manifest = build_manifest(layout, patterns)
    layout.state.mkdir(parents=True, exist_ok=True)
    layout.protected.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _diff(layout: Layout, manifest: dict) -> list[str]:
    problems = []
    current = _expand(layout, manifest["patterns"])
    for path, sha in sorted(manifest["files"].items()):
        if path not in current:
            problems.append(f"protected file missing: {path}")
        elif current[path] != sha:
            problems.append(f"protected file changed: {path}")
    for path in sorted(set(current) - set(manifest["files"])):
        problems.append(f"new file under a protected pattern: {path}")
    return problems


def check_working_tree(layout: Layout) -> list[str]:
    if not layout.protected.exists():
        return ["no protected manifest at state/protected.json"]
    manifest = json.loads(layout.protected.read_text(encoding="utf-8"))
    return _diff(layout, manifest)


def _git_show(layout: Layout, ref: str, relpath: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(layout.root), "show", f"{ref}:{relpath}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def check_against_base(layout: Layout, ref: str) -> list[str]:
    """Differences between the current frozen core and the core as approved on `ref`."""
    text = _git_show(layout, ref, "state/protected.json")
    if text is None:
        return [
            f"no protected manifest on {ref}: the whole frozen core is new relative to it "
            "and needs the maintainer's review"
        ]
    base = json.loads(text)
    problems = _diff(layout, base)
    if layout.protected.exists():
        now = json.loads(layout.protected.read_text(encoding="utf-8"))
        if now["patterns"] != base["patterns"]:
            problems.append("the list of protected patterns itself changed")
    else:
        problems.append("the protected manifest was deleted")
    return problems
