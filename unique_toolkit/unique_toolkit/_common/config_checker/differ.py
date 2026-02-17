"""Detect default value changes."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from unique_toolkit._common.config_checker.models import DefaultChange

logger = logging.getLogger(__name__)


@dataclass
class DefaultChangeReport:
    """Report of detected default changes."""

    config_name: str
    changes: list[DefaultChange]

    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return len(self.changes) > 0

    def format_summary(self) -> str:
        """Format changes as human-readable summary."""
        if not self.has_changes():
            return ""

        summary = f"Default changes in {self.config_name}:\n"
        for change in self.changes:
            old_str = (
                json.dumps(change.old_value)
                if not isinstance(change.old_value, str)
                else f'"{change.old_value}"'
            )
            new_str = (
                json.dumps(change.new_value)
                if not isinstance(change.new_value, str)
                else f'"{change.new_value}"'
            )
            summary += f"  - {change.field_path}: {old_str} → {new_str}\n"

        return summary


class ConfigDiffer:
    """Detect default value changes between versions."""

    def compare_defaults(
        self,
        old_json: dict[str, Any],
        new_instance: BaseModel,
    ) -> list[DefaultChange]:
        """Compare old JSON defaults with new instance defaults.

        Args:
            old_json: Defaults from base commit
            new_instance: Instance of new model with current defaults

        Returns:
            List of DefaultChange objects for any differences
        """
        new_json = new_instance.model_dump(mode="json")
        changes: list[DefaultChange] = []

        self._compare_recursive(old_json, new_json, "", changes)

        return changes

    @staticmethod
    def _compare_recursive(
        old: Any,
        new: Any,
        prefix: str,
        changes: list[DefaultChange],
    ) -> None:
        """Recursively compare old and new values.

        Args:
            old: Old value
            new: New value
            prefix: Current field path prefix
            changes: List to accumulate changes
        """
        # Both dicts
        if isinstance(old, dict) and isinstance(new, dict):
            all_keys = set(old.keys()) | set(new.keys())
            for key in all_keys:
                new_prefix = f"{prefix}.{key}" if prefix else key
                old_val = old.get(key)
                new_val = new.get(key)

                if key not in old:
                    # Key only in new (not a change, it's a new field)
                    continue
                if key not in new:
                    # Key removed (schema change, not a default change)
                    continue

                ConfigDiffer._compare_recursive(old_val, new_val, new_prefix, changes)

        # Both lists
        elif isinstance(old, list) and isinstance(new, list):
            if old != new:
                changes.append(
                    DefaultChange(field_path=prefix, old_value=old, new_value=new)
                )

        # Scalar values
        else:
            if old != new:
                changes.append(
                    DefaultChange(field_path=prefix, old_value=old, new_value=new)
                )
