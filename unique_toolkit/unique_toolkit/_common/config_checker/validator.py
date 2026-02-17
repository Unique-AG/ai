"""Validate old JSON against new schema."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from unique_toolkit._common.config_checker.differ import ConfigDiffer
from unique_toolkit._common.config_checker.models import (
    ConfigEntry,
    ConfigValidationResult,
)
from unique_toolkit._common.config_checker.models import (
    ValidationError as ValidationErrorModel,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Report of validation results."""

    total_configs: int
    valid_count: int
    invalid_count: int
    results: list[ConfigValidationResult]

    def has_failures(self) -> bool:
        """Check if there are any validation failures."""
        return self.invalid_count > 0

    def get_error_summary(self) -> str:
        """Get a human-readable summary of errors."""
        if not self.has_failures():
            return "All configs validated successfully"

        summary = f"Validation failed for {self.invalid_count}/{self.total_configs} configs:\n"
        for result in self.results:
            if not result.valid and result.errors:
                summary += f"\n{result.config_name}:\n"
                for error in result.errors:
                    summary += f"  - {error.field_path}: {error.message}\n"

        return summary


class ConfigValidator:
    """Validate old JSON against new schema."""

    def __init__(self):
        self.differ = ConfigDiffer()

    def validate_config(
        self,
        old_json: dict[str, Any],
        new_model: type[BaseModel],
        config_name: str = "",
    ) -> ConfigValidationResult:
        """Validate old JSON against new model schema.

        Args:
            old_json: Dictionary loaded from base commit's JSON export
            new_model: The current (tip commit) config model class
            config_name: Name of the config (for reporting)

        Returns:
            ConfigValidationResult with validation status and details
        """
        errors = []

        # 1. Structural Check: Detect removed fields
        old_keys = set(old_json.keys())
        new_keys = set(new_model.model_fields.keys())
        removed_keys = old_keys - new_keys

        for key in removed_keys:
            errors.append(
                ValidationErrorModel(
                    field_path=key,
                    message="Field was removed from the model (breaking change)",
                    old_value=old_json.get(key),
                )
            )

        try:
            # 2. Value Check: Try to validate/instantiate
            instance = new_model.model_validate(old_json)

            # If successful (and no removed fields), check for default changes
            try:
                # Instantiate a fresh instance with code-only defaults via model_construct()
                # This ensures we ignore the current environment when getting "tip" defaults.
                default_instance = new_model.model_construct()

                default_changes = self.differ.compare_defaults(
                    old_json, default_instance
                )
            except Exception:
                # Fallback to the validated instance if needed
                default_changes = self.differ.compare_defaults(old_json, instance)

            if not errors:
                return ConfigValidationResult(
                    config_name=config_name,
                    valid=True,
                    errors=None,
                    default_changes=default_changes if default_changes else None,
                )
            else:
                return ConfigValidationResult(
                    config_name=config_name,
                    valid=False,
                    errors=errors,
                    default_changes=None,
                )

        except ValidationError as e:
            # 3. Parse and Enhance Validation Errors
            new_errors = self._parse_validation_errors(e, old_json)

            # Heuristic: Try to identify renames
            # If we have removed fields AND 'missing' field errors, they might be renames
            missing_fields = [
                err.field_path
                for err in new_errors
                if "missing" in err.message.lower() or "required" in err.message.lower()
            ]

            if removed_keys and missing_fields:
                for err in new_errors:
                    if err.field_path in missing_fields:
                        # Suggest potential rename if there's exactly one removed field and one missing field
                        if len(removed_keys) == 1:
                            old_field = list(removed_keys)[0]
                            err.message += f" (Note: Field '{old_field}' was removed, maybe you renamed it?)"

            errors.extend(new_errors)

            return ConfigValidationResult(
                config_name=config_name,
                valid=False,
                errors=errors,
                default_changes=None,
            )

    def validate_all(
        self,
        artifact_dir: Path,
        config_entries: list[ConfigEntry],
        fail_on_missing: bool = False,
    ) -> ValidationReport:
        """Validate all configs from artifact directory.

        Args:
            artifact_dir: Directory containing exported JSON files
            config_entries: List of ConfigEntry objects for new schema
            fail_on_missing: Whether to fail if a config is missing at tip

        Returns:
            ValidationReport with all results
        """
        artifact_dir = Path(artifact_dir)
        results: list[ConfigValidationResult] = []

        # Build mapping of config names to models
        config_models = {entry.name: entry.model for entry in config_entries}

        # Load all JSON files
        json_files = list(artifact_dir.glob("*.json"))
        logger.info(f"Validating {len(json_files)} config files from {artifact_dir}")

        for json_file in json_files:
            if json_file.name == "manifest.json":
                continue

            config_name = json_file.stem

            try:
                with open(json_file, "r") as f:
                    old_json = json.load(f)

                # Find matching model
                if config_name not in config_models:
                    logger.warning(f"No model found for config: {config_name}")
                    result = ConfigValidationResult(
                        config_name=config_name,
                        valid=not fail_on_missing,
                        errors=[
                            ValidationErrorModel(
                                field_path="__root__",
                                message="Config class not found at tip (was removed or renamed)",
                            )
                        ],
                    )
                else:
                    result = self.validate_config(
                        old_json, config_models[config_name], config_name
                    )

                results.append(result)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON {json_file}: {e}")
                results.append(
                    ConfigValidationResult(
                        config_name=config_name,
                        valid=False,
                        errors=[
                            ValidationErrorModel(
                                field_path="__root__",
                                message=f"Invalid JSON: {e}",
                            )
                        ],
                    )
                )

        # Count results
        valid_count = sum(1 for r in results if r.valid)
        invalid_count = len(results) - valid_count

        report = ValidationReport(
            total_configs=len(results),
            valid_count=valid_count,
            invalid_count=invalid_count,
            results=results,
        )

        logger.info(
            f"Validation complete: {valid_count} valid, {invalid_count} invalid"
        )
        return report

    @staticmethod
    def _parse_validation_errors(
        validation_error: ValidationError,
        original_json: dict[str, Any],
    ) -> list[ValidationErrorModel]:
        """Parse Pydantic ValidationError into our format.

        Args:
            validation_error: The Pydantic ValidationError
            original_json: The original JSON being validated

        Returns:
            List of ValidationErrorModel objects
        """
        errors: list[ValidationErrorModel] = []

        for error in validation_error.errors():
            loc = error.get("loc", ())
            field_path = ".".join(str(x) for x in loc) if loc else "__root__"
            msg = error.get("msg", "Unknown error")
            error_type = error.get("type", "unknown")

            # Get the old value from original JSON
            old_value = None
            try:
                current = original_json
                for key in loc:
                    if isinstance(current, dict) and isinstance(key, str):
                        current = current.get(key)
                    elif isinstance(current, list) and isinstance(key, int):
                        try:
                            current = current[key]
                        except (IndexError, TypeError):
                            current = None
                            break
                    else:
                        current = None
                        break
                old_value = current
            except Exception:
                pass

            error_obj = ValidationErrorModel(
                field_path=field_path,
                message=f"{error_type}: {msg}",
                old_value=old_value,
            )
            errors.append(error_obj)

        return errors
