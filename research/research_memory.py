"""Scoped validation-only search memory. Integrity checks, not cryptographic trust.

The API accepts registered candidates and validation scores only. An operator
with file access can rewrite an entire chain; reviewed version control remains
necessary. No test outcome field is accepted.
"""
import hashlib
import json
import math
from pathlib import Path


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


class ResearchMemory:
    def __init__(self, path, scope, validate):
        self.path = Path(path)
        self.scope = scope
        self.validate = validate
        self.rows = []
        previous = "0" * 64
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                observed = record.pop("sha256")
                if set(record) != {"scope", "previous", "candidate", "validation_score"}:
                    raise ValueError("memory record has forbidden or missing fields")
                if record["scope"] != scope or record["previous"] != previous or sha(record) != observed:
                    raise ValueError("memory scope or hash chain differs")
                validate(record["candidate"])
                if not math.isfinite(record["validation_score"]):
                    raise ValueError("nonfinite memory score")
                record["sha256"] = observed
                self.rows.append(record)
                previous = observed

    def append(self, candidate, validation_score):
        self.validate(candidate)
        if type(validation_score) not in (int, float) or not math.isfinite(validation_score):
            raise ValueError("finite validation score required")
        record = {"scope": self.scope, "previous": self.rows[-1]["sha256"] if self.rows else "0" * 64,
                  "candidate": candidate, "validation_score": float(validation_score)}
        record["sha256"] = sha(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        self.rows.append(record)

    @property
    def head(self):
        return self.rows[-1]["sha256"] if self.rows else "0" * 64
