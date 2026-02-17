"""Config model discovery and registration."""

import logging
from pathlib import Path

from pydantic import BaseModel

from unique_toolkit._common.config_checker.models import ConfigEntry

logger = logging.getLogger(__name__)

# Global registry for explicit registrations
_GLOBAL_EXPLICIT_REGISTRY: dict[str, type[BaseModel]] = {}


def _clear_global_registry():
    """Clear the global explicit registry (used for testing only)."""
    global _GLOBAL_EXPLICIT_REGISTRY
    _GLOBAL_EXPLICIT_REGISTRY.clear()


def register_config(name: str | None = None):
    """Decorator to explicitly register a config model (REQUIRED).

    Configs MUST be explicitly registered using this decorator to be included
    in compatibility checks. This ensures teams own and declare what configs
    they want to protect.

    Args:
        name: Custom name for the config. If None, uses the class name.

    Example:
        @register_config(name="web_search_settings")
        class Settings(BaseSettings):
            ...

    Example (with automatic name):
        @register_config()
        class WebSearchConfig(BaseModel):
            ...
    """

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        config_name = name or cls.__name__
        _GLOBAL_EXPLICIT_REGISTRY[config_name] = cls
        logger.debug(
            f"Explicitly registered config: {config_name} -> {cls.__module__}.{cls.__name__}"
        )
        return cls

    return decorator


class ConfigRegistry:
    """Manage explicitly registered config models."""

    def __init__(self):
        self._explicit_configs: dict[str, ConfigEntry] = {}

    def discover_configs(self, package_path: Path) -> list[ConfigEntry]:
        """Load explicitly registered config models by scanning the package.

        NOTE: This scans the directory for Python files and imports them to
        trigger the @register_config decorators.

        Args:
            package_path: Root path of the package to scan

        Returns:
            List of explicitly registered ConfigEntry objects
        """
        import importlib.util
        import sys

        package_path = Path(package_path).resolve()

        if not package_path.exists():
            logger.warning(f"Package path does not exist: {package_path}")
            return []

        # Find source directory if it's a standard repo structure
        src_dir = package_path / "src"
        if src_dir.exists():
            search_path = src_dir
        else:
            search_path = package_path

        logger.debug(f"Scanning for configs in: {search_path}")

        # Add search path to sys.path so imports work
        if str(search_path) not in sys.path:
            sys.path.insert(0, str(search_path))

        # Scan for Python files recursively
        for py_file in search_path.rglob("*.py"):
            # Skip hidden files, __pycache__, .venv, etc.
            # Use relative path to only check for hidden directories within the scan root
            try:
                relative_py_file = py_file.relative_to(search_path)
            except ValueError:
                # Should not happen with rglob but being safe
                continue

            if any(
                part.startswith(".") or part == "__pycache__" or part == ".venv"
                for part in relative_py_file.parts
            ):
                continue

            # Try to import the module
            try:
                # Convert path to module name relative to search path
                relative_path = py_file.relative_to(search_path)
                module_name = ".".join(relative_path.with_suffix("").parts)

                if module_name in sys.modules:
                    # Already imported
                    continue

                logger.debug(f"Importing module to discover configs: {module_name}")
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
            except Exception as e:
                # Log but continue scanning other files
                logger.debug(f"Failed to import {py_file} for discovery: {e}")

        # After importing everything, gather what's in the global registry
        configs = self.get_all_configs()
        logger.debug(f"Discovered {len(configs)} explicitly registered config(s)")

        return configs

    def register_explicit(self, model: type[BaseModel], name: str) -> None:
        """Register a config model explicitly (via decorator).

        Args:
            model: The BaseModel subclass to register
            name: Name for the config
        """
        config_entry = ConfigEntry(
            name=name,
            model=model,
            source="explicit",
            module_path=None,
        )
        self._explicit_configs[name] = config_entry
        logger.debug(f"Registered explicit config: {name}")

    def get_all_configs(self, include_discovered: bool = False) -> list[ConfigEntry]:
        """Get all registered configs.

        Args:
            include_discovered: Ignored (auto-discovery is disabled).
                                Kept for API compatibility.

        Returns:
            List of all explicitly registered ConfigEntry objects
        """
        result = {}

        # Add explicit configs
        result.update({entry.name: entry for entry in self._explicit_configs.values()})

        # Also include any from global registry that weren't loaded yet
        for name, model in _GLOBAL_EXPLICIT_REGISTRY.items():
            if name not in result:
                config_entry = ConfigEntry(
                    name=name,
                    model=model,
                    source="explicit",
                    module_path=None,
                )
                result[name] = config_entry

        return list(result.values())

    def load_from_package(self, package_path: Path) -> None:
        """Load configs from a package.

        This is a convenience method that loads explicitly registered configs.

        Args:
            package_path: Root path of the package
        """
        self.discover_configs(package_path)
