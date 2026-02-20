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
            summary += f"  - {change.field_path}: {json.dumps(change.old_value)} → {json.dumps(change.new_value)}\n"

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
        from unique_toolkit._common.config_checker.exporter import ConfigExporter

        new_json = ConfigExporter._serialize_model(new_instance)
        changes: list[DefaultChange] = []
        diff = DeepDiff(old_json, new_json, ignore_order=True)

        if diff:
            for path, change_info in diff.get("values_changed", {}).items():
                field_path = self._path_to_dot_notation(path)
                changes.append(
                    DefaultChange(
                        field_path=field_path,
                        old_value=change_info.get("old_value"),
                        new_value=change_info.get("new_value"),
                    )
                )

            for path, change_info in diff.get("type_changes", {}).items():
                field_path = self._path_to_dot_notation(path)
                changes.append(
                    DefaultChange(
                        field_path=field_path,
                        old_value=change_info.get("old_value"),
                        new_value=change_info.get("new_value"),
                    )
                )

            for path in diff.get("dictionary_item_added", []):
                field_path = self._path_to_dot_notation(path)
                if "." not in field_path:
                    continue

                new_value = ConfigDiffer._get_nested_value(new_json, path)
                changes.append(
                    DefaultChange(
                        field_path=field_path,
                        old_value=None,
                        new_value=new_value,
                    )
                )

            for path in diff.get("dictionary_item_removed", []):
                field_path = self._path_to_dot_notation(path)
                if "." not in field_path:
                    continue

                old_value = ConfigDiffer._get_nested_value(old_json, path)
                changes.append(
                    DefaultChange(
                        field_path=field_path,
                        old_value=old_value,
                        new_value=None,
                    )
                )

            list_changes: set[str] = set()
            for path in diff.get("iterable_item_added", []):
                parent_path = ConfigDiffer._extract_parent_path(path)
                if parent_path:
                    list_changes.add(parent_path)

            for path in diff.get("iterable_item_removed", []):
                parent_path = ConfigDiffer._extract_parent_path(path)
                if parent_path:
                    list_changes.add(parent_path)

            for parent_path in list_changes:
                field_path = self._path_to_dot_notation(parent_path)
                if any(c.field_path == field_path for c in changes):
                    continue

                changes.append(
                    DefaultChange(
                        field_path=field_path,
                        old_value=ConfigDiffer._get_nested_value(old_json, parent_path),
                        new_value=ConfigDiffer._get_nested_value(new_json, parent_path),
                    )
                )

        return sorted(changes, key=lambda x: x.field_path)

    @staticmethod
    def _extract_parent_path(path: str) -> str:
        """Extract parent path by removing the last index/key.

        Examples:
            root['items'][0] -> root['items']
            root['config']['tags'][1] -> root['config']['tags']
        """
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
        parts = re.findall(r"\[['\"]?([^'\"\]]+)['\"]?\]", path)
        return ".".join(parts)
