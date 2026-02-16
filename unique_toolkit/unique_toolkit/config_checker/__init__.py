"""Configuration breaking change detection system.

This module provides tools to detect and report breaking changes in configuration
models by comparing defaults at merge-base vs tip of PR.

Key components:
- ConfigRegistry: Auto-discover and explicitly register config models
- ConfigExporter: Export config defaults to JSON artifacts
- ConfigValidator: Validate old JSON against new schema
- ConfigDiffer: Detect non-breaking default value changes
- CLI: export and check commands
"""

from unique_toolkit.config_checker.differ import ConfigDiffer, DefaultChangeReport
from unique_toolkit.config_checker.exporter import ConfigExporter, ExportManifest
from unique_toolkit.config_checker.registry import (
    ConfigEntry,
    ConfigRegistry,
    register_config,
)
from unique_toolkit.config_checker.validator import ConfigValidator, ValidationReport

__all__ = [
    "register_config",
    "ConfigRegistry",
    "ConfigEntry",
    "ConfigExporter",
    "ExportManifest",
    "ConfigValidator",
    "ValidationReport",
    "ConfigDiffer",
    "DefaultChangeReport",
]
