"""Repository layout. All paths hang off one root so tests can use a temp copy."""
from __future__ import annotations

from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


class Layout:
    def __init__(self, root: Path | str | None = None):
        self.root = Path(root) if root else DEFAULT_ROOT

    @property
    def cards(self) -> Path:
        return self.root / "cards"

    @property
    def experiments(self) -> Path:
        return self.root / "experiments"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def ledger(self) -> Path:
        return self.state / "ledger.jsonl"

    @property
    def sources(self) -> Path:
        return self.state / "sources.jsonl"

    def card_path(self, card_id: str) -> Path:
        return self.cards / f"{card_id}.json"

    def lock_path(self, card_id: str) -> Path:
        return self.cards / f"{card_id}.lock.json"

    def run_path(self, run_id: str) -> Path:
        return self.runs / f"{run_id}.json"

    def report_path(self, card_id: str) -> Path:
        return self.reports / f"{card_id}.md"

    def notes_path(self, card_id: str) -> Path:
        return self.reports / f"{card_id}.notes.md"

    def experiment_path(self, name: str) -> Path:
        return self.experiments / f"{name}.py"
