"""Config model discovery and registration."""

import logging
import sys
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel

from unique_toolkit._common.config_checker.models import ConfigEntry

logger = logging.getLogger(__name__)


@contextmanager
def _isolated_import_path(path: Path):
    """Temporarily add path to sys.path for imports; restore on exit.

    Avoids persistent global side effects and import conflicts when
    multiple packages are discovered in the same process.
    """
    old_path = sys.path.copy()
    try:
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
        yield
    finally:
        sys.path = old_path


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

        package_path = Path(package_path).resolve()

        if not package_path.exists():
            logger.warning(f"Package path does not exist: {package_path}")
            return []

        src_dir = package_path / "src"
        if src_dir.exists():
            search_path = src_dir
        else:
            search_path = package_path

        logger.debug(f"Scanning for configs in: {search_path}")

        with _isolated_import_path(search_path):
            configs = self._discover_configs_under(search_path)

        logger.debug(f"Discovered {len(configs)} explicitly registered config(s)")
        return configs

    def _discover_configs_under(self, search_path: Path) -> list[ConfigEntry]:
        """Discover configs under search_path (sys.path must include search_path)."""
        import importlib.util

        # Only files under search_path are loaded (relative_to enforces this).
        for py_file in search_path.rglob("*.py"):
            try:
                # Quick static check to avoid importing files that don't contain the decorator
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if "@register_config" not in content:
                    continue

                relative_py_file = py_file.relative_to(search_path)
            except (ValueError, OSError):
                continue

            if any(
                part.startswith(".") or part == "__pycache__" or part == ".venv"
                for part in relative_py_file.parts
            ):
                continue

            try:
                module_name = ".".join(relative_py_file.with_suffix("").parts)

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
        return self.get_all_configs()

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

    def get_all_configs(self) -> list[ConfigEntry]:
        """Get all registered configs.


        Returns:
            List of all explicitly registered ConfigEntry objects
        """
        result = {}

        result.update({entry.name: entry for entry in self._explicit_configs.values()})
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
        logger.debug(f"Loaded registered config(s) from package: {package_path}")
