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

from typing import TYPE_CHECKING

from unique_toolkit._common._lazy import install as _install

if TYPE_CHECKING:
    from unique_toolkit._common.config_checker.differ import (
        ConfigDiffer as ConfigDiffer,
    )
    from unique_toolkit._common.config_checker.differ import (
        DefaultChangeReport as DefaultChangeReport,
    )
    from unique_toolkit._common.config_checker.exporter import (
        ConfigExporter as ConfigExporter,
    )
    from unique_toolkit._common.config_checker.exporter import (
        ExportManifest as ExportManifest,
    )
    from unique_toolkit._common.config_checker.models import ConfigEntry as ConfigEntry
    from unique_toolkit._common.config_checker.registry import (
        ConfigRegistry as ConfigRegistry,
    )
    from unique_toolkit._common.config_checker.registry import (
        register_config as register_config,
    )
    from unique_toolkit._common.config_checker.validator import (
        ConfigValidator as ConfigValidator,
    )
    from unique_toolkit._common.config_checker.validator import (
        ValidationReport as ValidationReport,
    )

_EXPORTS: dict[str, tuple[str, str]] = {
    "ConfigDiffer": ("unique_toolkit._common.config_checker.differ", "ConfigDiffer"),
    "DefaultChangeReport": (
        "unique_toolkit._common.config_checker.differ",
        "DefaultChangeReport",
    ),
    "ConfigExporter": (
        "unique_toolkit._common.config_checker.exporter",
        "ConfigExporter",
    ),
    "ExportManifest": (
        "unique_toolkit._common.config_checker.exporter",
        "ExportManifest",
    ),
    "ConfigEntry": ("unique_toolkit._common.config_checker.models", "ConfigEntry"),
    "ConfigRegistry": (
        "unique_toolkit._common.config_checker.registry",
        "ConfigRegistry",
    ),
    "register_config": (
        "unique_toolkit._common.config_checker.registry",
        "register_config",
    ),
    "ConfigValidator": (
        "unique_toolkit._common.config_checker.validator",
        "ConfigValidator",
    ),
    "ValidationReport": (
        "unique_toolkit._common.config_checker.validator",
        "ValidationReport",
    ),
}

__all__ = list(_EXPORTS)

_install(globals(), _EXPORTS)
