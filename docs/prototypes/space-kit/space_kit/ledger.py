"""Append-only record of the spaces this machine created or deleted."""

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from space_kit.base import JsonObject, KitModel, SpaceKitError

LEDGER_DIR = "ledger"
LEDGER_FILE = "spaces.jsonl"
DRY_RUN_DIR = "dry-runs"


class LedgerAction(StrEnum):
    CREATED = "created"
    EDITED = "edited"
    DELETED = "deleted"


class LedgerEntry(KitModel):
    at: datetime
    action: LedgerAction
    target: str
    space_id: str
    name: str
    template_id: str = ""
    source_target: str = ""
    changed_paths: tuple[str, ...] = ()
    registered_profile: str = ""


class Ledger:
    def __init__(self, *, home: Path) -> None:
        self._dir: Path = home / LEDGER_DIR

    @property
    def path(self) -> Path:
        return self._dir / LEDGER_FILE

    def append(self, *, entry: LedgerEntry) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            _ = handle.write(entry.model_dump_json() + "\n")

    def entries(self) -> list[LedgerEntry]:
        if not self.path.exists():
            return []
        entries: list[LedgerEntry] = []
        for number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                entries.append(LedgerEntry.model_validate_json(line))
            except ValueError as exc:
                msg = f"{self.path}:{number} is not a ledger entry: {exc}"
                raise SpaceKitError(msg) from exc
        return entries

    def live_space_ids(self, *, target: str) -> set[str]:
        """Spaces created on `target` by this machine and not deleted."""
        alive: set[str] = set()
        for entry in self.entries():
            if entry.target != target:
                continue
            if entry.action is LedgerAction.CREATED:
                alive.add(entry.space_id)
            elif entry.action is LedgerAction.DELETED:
                alive.discard(entry.space_id)
        return alive

    def write_dry_run(self, *, name: str, payload: JsonObject) -> Path:
        directory = self._dir / DRY_RUN_DIR
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name)
        path = directory / f"{stamp}-{safe}.json"
        _ = path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path


def now() -> datetime:
    return datetime.now(UTC)
