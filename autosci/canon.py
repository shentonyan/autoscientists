"""Canonical serialisation and hashing.

Everything the framework locks or chains is hashed through these helpers so that
two machines that agree on content also agree on the digest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, UTF-8 characters kept."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def digest(obj: Any) -> str:
    return sha256_text(canonical(obj))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
