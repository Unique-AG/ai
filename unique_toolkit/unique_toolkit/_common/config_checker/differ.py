"""Detect default value changes."""

import json
import logging
import re
from typing import Any

from deepdiff import DeepDiff
from pydantic import BaseModel, Field

from unique_toolkit._common.config_checker.models import DefaultChange

logger = logging.getLogger(__name__)


class DefaultChangeReport(BaseModel):
    """Report of detected default changes."""

    config_name: str
    changes: list[DefaultChange] = Field(default_factory=list)

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
                if not isinstance(change.old_value, (str, int, float, bool, type(None)))
                else json.dumps(change.old_value)
            )
            new_str = (
                json.dumps(change.new_value)
                if not isinstance(change.new_value, (str, int, float, bool, type(None)))
                else json.dumps(change.new_value)
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
        # Use the robust serialization from exporter to handle secrets correctly
        from unique_toolkit._common.config_checker.exporter import ConfigExporter

        new_json = ConfigExporter._serialize_model(new_instance)
        changes: list[DefaultChange] = []

        self._compare_recursive(old_json, new_json, "", changes)

        return sorted(changes, key=lambda x: x.field_path)

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
        # Both dicts: recurse into keys that exist in both
        if isinstance(old, dict) and isinstance(new, dict):
            # We only care about fields that exist in both (schema changes are handled by validator)
            common_keys = set(old.keys()) & set(new.keys())
            for key in common_keys:
                new_prefix = f"{prefix}.{key}" if prefix else key
                ConfigDiffer._compare_recursive(old[key], new[key], new_prefix, changes)

        # Both lists: use DeepDiff for robust semantic comparison (ignoring order)
        elif isinstance(old, list) and isinstance(new, list):
            if DeepDiff(old, new, ignore_order=True):
                changes.append(
                    DefaultChange(field_path=prefix, old_value=old, new_value=new)
                )

        # Scalar values or type changes
        else:
            if old != new:
                changes.append(
                    DefaultChange(field_path=prefix, old_value=old, new_value=new)
                )

    @staticmethod
    def _parse_deepdiff_path(path: str) -> str:
        """Convert DeepDiff path (root['a']['b']) to dot notation (a.b)."""
        # Keep this for utility, though not used in the hybrid approach
        parts = re.findall(r"\[['\"]?([^'\"\]]+)['\"]?\]", path)
        return ".".join(parts)
