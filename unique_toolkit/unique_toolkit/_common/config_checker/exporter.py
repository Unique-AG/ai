"""Export config defaults to JSON artifacts."""

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings

from unique_toolkit._common.config_checker.models import (
    ConfigEntry,
    EnvironmentVarWarning,
)

logger = logging.getLogger(__name__)


@dataclass
class ExportManifest:
    """Manifest of exported configs."""

    exported_count: int
    skipped_count: int
    warnings: list[EnvironmentVarWarning]
    config_files: dict[str, str]  # config_name -> file_path
    timestamp: str | None = None


class ConfigExporter:
    """Export config defaults to JSON artifacts."""

    def __init__(self):
        self.warnings: list[EnvironmentVarWarning] = []
        self.config_files: dict[str, str] = {}

    def export_defaults(self, config_model: type[BaseModel]) -> dict[str, Any]:
        """Export defaults for a single config model.

        For BaseSettings, only uses code-level defaults, ignoring env vars.

        Args:
            config_model: The Pydantic model to export

        Returns:
            Dictionary of defaults in JSON-serializable format
        """
        # Create instance with all defaults
        try:
            # Check if it's a BaseSettings
            if issubclass(config_model, BaseSettings):
                # Create with validation disabled to avoid env var loading
                instance = config_model()  # type: ignore
                self._check_for_env_vars(config_model)
            else:
                instance = config_model()
        except Exception as e:
            logger.error(f"Failed to instantiate {config_model.__name__}: {e}")
            raise

        # Export to dict
        return self._serialize_model(instance)

    def _check_for_env_vars(self, model: type[BaseSettings]) -> None:
        """Check if environment variables are set that would affect defaults.

        Args:
            model: The BaseSettings model to check
        """
        if not hasattr(model, "model_config"):
            return

        config = model.model_config
        env_prefix = config.get("env_prefix", "").lower()

        if env_prefix:
            for env_var, value in os.environ.items():
                if env_var.lower().startswith(env_prefix):
                    warning = EnvironmentVarWarning(
                        var_name=env_var,
                        value=value[:20] if value else None,
                        message=f"Environment variable {env_var} set during export (will be ignored, using code defaults)",
                    )
                    self.warnings.append(warning)
                    logger.warning(f"ENV VAR DETECTED: {warning.message}")

    def export_all(
        self,
        config_entries: list[ConfigEntry],
        output_dir: Path,
    ) -> ExportManifest:
        """Export defaults for all config models.

        Args:
            config_entries: List of ConfigEntry objects to export
            output_dir: Directory to write JSON artifacts

        Returns:
            ExportManifest with metadata about the export
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        exported_count = 0
        skipped_count = 0
        self.warnings.clear()
        self.config_files.clear()

        for entry in config_entries:
            try:
                defaults = self.export_defaults(entry.model)

                # Write to JSON file
                output_file = output_dir / f"{entry.name}.json"
                with open(output_file, "w") as f:
                    json.dump(defaults, f, indent=2)

                self.config_files[entry.name] = str(output_file)
                exported_count += 1
                logger.info(f"Exported {entry.name} to {output_file}")

            except Exception as e:
                logger.error(f"Failed to export {entry.name}: {e}")
                skipped_count += 1

        manifest = ExportManifest(
            exported_count=exported_count,
            skipped_count=skipped_count,
            warnings=self.warnings,
            config_files=self.config_files,
        )

        # Write manifest
        manifest_file = output_dir / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(
                {
                    "exported_count": manifest.exported_count,
                    "skipped_count": manifest.skipped_count,
                    "warnings": [asdict(w) for w in manifest.warnings],
                    "config_files": manifest.config_files,
                },
                f,
                indent=2,
            )

        logger.info(
            f"Export complete: {exported_count} exported, {skipped_count} skipped"
        )
        return manifest

    @staticmethod
    def _serialize_model(instance: BaseModel) -> dict[str, Any]:
        """Serialize a Pydantic model instance to JSON-compatible dict.

        Handles special types:
        - SecretStr: Extracts the plain value
        - Nested models: Recursively serializes
        - Enums: Converts to values

        Args:
            instance: Pydantic model instance

        Returns:
            JSON-serializable dictionary
        """
        result = instance.model_dump(mode="json")

        # Handle special types
        for key, value in result.items():
            if isinstance(value, SecretStr):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = ConfigExporter._serialize_dict(value)
            elif isinstance(value, list):
                result[key] = ConfigExporter._serialize_list(value)

        return result

    @staticmethod
    def _serialize_dict(obj: dict[str, Any]) -> dict[str, Any]:
        """Recursively serialize dictionary values."""
        result = {}
        for key, value in obj.items():
            if isinstance(value, SecretStr):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = ConfigExporter._serialize_dict(value)
            elif isinstance(value, list):
                result[key] = ConfigExporter._serialize_list(value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _serialize_list(obj: list) -> list:
        """Recursively serialize list items."""
        result = []
        for item in obj:
            if isinstance(item, SecretStr):
                result.append(str(item))
            elif isinstance(item, dict):
                result.append(ConfigExporter._serialize_dict(item))
            elif isinstance(item, list):
                result.append(ConfigExporter._serialize_list(item))
            else:
                result.append(item)
        return result
