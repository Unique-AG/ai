"""Export config defaults to JSON artifacts."""

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import date
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
        self.detected_env_vars: set[str] = set()

    def export_defaults(self, config_model: type[BaseModel]) -> dict[str, Any]:
        """Export defaults for a single config model.

        For BaseSettings, only uses code-level defaults, ignoring env vars.

        Args:
            config_model: The Pydantic model to export

        Returns:
            Dictionary of defaults in JSON-serializable format
        """
        # Create instance with all defaults using model_construct()
        # This bypasses validation and settings sources (like environment variables)
        # while still populating code-level defaults and default_factories.
        try:
            instance = config_model.model_construct()
            if issubclass(config_model, BaseSettings):
                self._check_for_env_vars(config_model)
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
        config = getattr(model, "model_config", {})
        env_prefix = config.get("env_prefix", "")

        # Check all env vars against prefix AND field names
        field_names = set(model.model_fields.keys())

        for env_var in os.environ:
            # Check prefix (case-insensitive)
            if env_prefix and env_var.lower().startswith(env_prefix.lower()):
                self.detected_env_vars.add(env_var)
                continue

            # Check field names (case-insensitive)
            if env_var.lower() in {f.lower() for f in field_names}:
                self.detected_env_vars.add(env_var)

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
        self.detected_env_vars.clear()

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

        # Add consolidated warning if env vars were detected
        if self.detected_env_vars:
            vars_str = ", ".join(sorted(self.detected_env_vars))
            msg = f"Environment variables detected during export: {vars_str}. These were ignored to ensure a secure, code-only export of defaults."
            self.warnings.append(
                EnvironmentVarWarning(var_name="MULTIPLE", message=msg)
            )
            logger.warning(msg)

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
        # Use model_dump() without mode="json" to keep SecretStr objects intact
        # so we can call .get_secret_value() on them.
        data = instance.model_dump()
        return ConfigExporter._serialize_any(data)

    @staticmethod
    def _serialize_any(value: Any) -> Any:
        """Recursively serialize any value to JSON-compatible format."""
        if isinstance(value, SecretStr):
            # Security: Never export plain-text secrets to artifacts.
            # Instead, export a deterministic hash so we can still detect changes
            # without leaking the actual value.
            secret_val = value.get_secret_value()
            if not secret_val:
                return ""
            hash_val = hashlib.sha256(secret_val.encode()).hexdigest()
            return f"secret_hash:sha256:{hash_val}"
        if isinstance(value, BaseModel):
            return ConfigExporter._serialize_model(value)
        if isinstance(value, dict):
            return {k: ConfigExporter._serialize_any(v) for k, v in value.items()}
        if isinstance(value, list):
            return [ConfigExporter._serialize_any(v) for v in value]
        if hasattr(value, "value") and not isinstance(
            value, type
        ):  # Enums or custom objects like FeatureFlag
            return ConfigExporter._serialize_any(value.value)
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, date):
            return value.isoformat()
        return value
