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

        Uses DeepDiff for semantic comparison (ignoring order in lists).

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

        # Single DeepDiff call handles all cases: nested dicts, lists (ignoring order), scalars
        diff = DeepDiff(old_json, new_json, ignore_order=True)

        if diff:
            # Extract value changes (most common: scalar changes, nested structure changes)
            for path, change_info in diff.get("values_changed", {}).items():
                field_path = self._path_to_dot_notation(path)
                changes.append(
                    DefaultChange(
                        field_path=field_path,
                        old_value=change_info.get("old_value"),
                        new_value=change_info.get("new_value"),
                    )
                )

            # Extract type changes (e.g., str -> int)
            for path, change_info in diff.get("type_changes", {}).items():
                field_path = self._path_to_dot_notation(path)
                changes.append(
                    DefaultChange(
                        field_path=field_path,
                        old_value=change_info.get("old_value"),
                        new_value=change_info.get("new_value"),
                    )
                )

            # Handle dictionary key changes (added/removed keys within dicts)
            # Extract parent dict and report as a change
            for path in diff.get("dictionary_item_added", []):
                self._report_structural_change(path, old_json, new_json, changes)

            for path in diff.get("dictionary_item_removed", []):
                self._report_structural_change(path, old_json, new_json, changes)

            # Handle list item changes (added/removed items in lists)
            # Extract parent list and report as a change
            for path in diff.get("iterable_item_added", []):
                self._report_structural_change(path, old_json, new_json, changes)

            for path in diff.get("iterable_item_removed", []):
                self._report_structural_change(path, old_json, new_json, changes)

        return sorted(changes, key=lambda x: x.field_path)

    @staticmethod
    def _report_structural_change(
        path: str,
        old_json: dict[str, Any],
        new_json: dict[str, Any],
        changes: list[DefaultChange],
    ) -> None:
        """Report a structural change (dict key or list item added/removed).

        Extracts the parent container and adds it to changes list.

        Args:
            path: DeepDiff path to the changed item
            old_json: Original config
            new_json: Updated config
            changes: List to accumulate changes
        """
        # Extract parent path (e.g., root['items'][0] -> root['items'])
        parent_path = ConfigDiffer._extract_parent_path(path)
        if not parent_path:
            return

        field_path = ConfigDiffer._path_to_dot_notation(parent_path)

        # Avoid duplicates: only add if not already reporting this parent
        if any(c.field_path == field_path for c in changes):
            return

        # Get parent values from old and new configs
        old_value = ConfigDiffer._get_nested_value(old_json, parent_path)
        new_value = ConfigDiffer._get_nested_value(new_json, parent_path)

        if old_value is not None or new_value is not None:
            changes.append(
                DefaultChange(
                    field_path=field_path,
                    old_value=old_value,
                    new_value=new_value,
                )
            )

    @staticmethod
    def _extract_parent_path(path: str) -> str:
        """Extract parent path by removing the last index/key.

        Examples:
            root['items'][0] -> root['items']
            root['config']['tags'][1] -> root['config']['tags']
            root['meta']['version'] -> root['meta']
        """
        # Remove the last bracket-enclosed index or key
        parent = re.sub(r"\[['\"]?[^'\"\]]+['\"]?\]$", "", path)
        return parent if parent != path and parent else ""

    @staticmethod
    def _get_nested_value(data: dict[str, Any], path: str) -> Any:
        """Get a nested value from a dict using DeepDiff path notation.

        Args:
            data: Dict to traverse
            path: DeepDiff path (e.g., root['a']['b'])

        Returns:
            The nested value or None if not found
        """
        # Extract keys from path: root['a']['b'] -> ['a', 'b']
        keys = re.findall(r"\[['\"]?([^'\"\]]+)['\"]?\]", path)
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, (list, tuple)):
                try:
                    current = current[int(key)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current

    @staticmethod
    def _path_to_dot_notation(path: str) -> str:
        """Convert DeepDiff path (root['a']['b']) to dot notation (a.b)."""
        # Extract bracket-enclosed keys/indices: root['name'] -> name
        parts = re.findall(r"\[['\"]?([^'\"\]]+)['\"]?\]", path)
        return ".".join(parts)
