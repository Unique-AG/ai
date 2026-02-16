"""Config model discovery and registration."""

import importlib
import inspect
import logging
import sys
from pathlib import Path

from pydantic import BaseModel

from unique_toolkit.config_checker.models import ConfigEntry

logger = logging.getLogger(__name__)

# Global registry for explicit registrations
_global_explicit_registry: dict[str, type[BaseModel]] = {}


def register_config(name: str | None = None):
    """Decorator to explicitly register a config model (optional).

    Args:
        name: Custom name for the config. If None, uses the class name.

    Example:
        @register_config(name="web_search_settings")
        class Settings(BaseSettings):
            ...
    """

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        config_name = name or cls.__name__
        _global_explicit_registry[config_name] = cls
        logger.debug(
            f"Explicitly registered config: {config_name} -> {cls.__module__}.{cls.__name__}"
        )
        return cls

    return decorator


class ConfigRegistry:
    """Discover and manage registered config models."""

    def __init__(self):
        self._discovered_configs: dict[str, ConfigEntry] = {}
        self._explicit_configs: dict[str, ConfigEntry] = {}

    def discover_configs(self, package_path: Path) -> list[ConfigEntry]:
        """Auto-discover config models in package.

        Scans for:
        - Classes matching *Config or *Settings patterns
        - In files named config.py
        - Excluding classes with _skip_config_check = True

        Args:
            package_path: Root path of the package to scan

        Returns:
            List of discovered ConfigEntry objects
        """
        self._discovered_configs.clear()
        package_path = Path(package_path).resolve()

        if not package_path.exists():
            logger.warning(f"Package path does not exist: {package_path}")
            return []

        # Find all config.py files, excluding common non-source directories
        config_files = []
        for path in package_path.rglob("config.py"):
            # Skip hidden directories, virtual envs, and cache
            if any(
                part.startswith(".") or part in ("__pycache__", "venv", "node_modules")
                for part in path.parts
            ):
                continue
            config_files.append(path)

        logger.debug(f"Found {len(config_files)} config.py files in {package_path}")

        for config_file in config_files:
            self._scan_config_file(config_file, package_path)

        return list(self._discovered_configs.values())

    def _scan_config_file(self, config_file: Path, package_root: Path) -> None:
        """Scan a single config.py file for BaseModel subclasses."""
        try:
            spec = importlib.util.spec_from_file_location("_config_module", config_file)
            if spec is None or spec.loader is None:
                logger.warning(f"Could not load spec for {config_file}")
                return

            module = importlib.util.module_from_spec(spec)
            sys.modules["_config_module"] = module
            spec.loader.exec_module(module)

            # Scan for BaseModel subclasses
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Skip if not a BaseModel subclass
                if not issubclass(obj, BaseModel) or obj is BaseModel:
                    continue

                # Skip if explicitly marked to skip
                if getattr(obj, "_skip_config_check", False):
                    logger.debug(
                        f"Skipping config (marked _skip_config_check): {obj.__name__}"
                    )
                    continue

                # Check if name matches convention
                if not self._matches_config_convention(name):
                    continue

                # Skip if defined in a parent module (not directly in this file)
                if obj.__module__ != "_config_module":
                    continue

                config_entry = ConfigEntry(
                    name=name,
                    model=obj,
                    source="auto_discovery",
                    module_path=str(config_file.relative_to(package_root)),
                )
                self._discovered_configs[name] = config_entry
                logger.debug(
                    f"Auto-discovered config: {name} from {config_entry.module_path}"
                )

        except Exception as e:
            logger.warning(f"Error scanning {config_file}: {e}")
        finally:
            # Clean up module
            sys.modules.pop("_config_module", None)

    @staticmethod
    def _matches_config_convention(name: str) -> bool:
        """Check if a class name matches config naming convention."""
        return name.endswith("Config") or name.endswith("Settings")

    def register_explicit(self, model: type[BaseModel], name: str) -> None:
        """Register a config model explicitly (via decorator).

        Args:
            model: The BaseModel subclass to register
            name: Name for the config
        """
        config_entry = ConfigEntry(
            name=name,
            model=model,
            source="explicit_decorator",
            module_path=None,
        )
        self._explicit_configs[name] = config_entry
        logger.debug(f"Registered explicit config: {name}")

    def get_all_configs(self, include_discovered: bool = True) -> list[ConfigEntry]:
        """Get all registered configs.

        Explicit registrations take precedence over discovered configs with the same name.

        Args:
            include_discovered: Whether to include auto-discovered configs

        Returns:
            List of all ConfigEntry objects (unique by name, explicit first)
        """
        result = {}

        # Add discovered first
        if include_discovered:
            result.update(
                {entry.name: entry for entry in self._discovered_configs.values()}
            )

        # Add explicit (overwrites any discovered with same name)
        result.update({entry.name: entry for entry in self._explicit_configs.values()})

        # Also include any from global registry that weren't loaded yet
        for name, model in _global_explicit_registry.items():
            if name not in result:
                config_entry = ConfigEntry(
                    name=name,
                    model=model,
                    source="explicit_decorator",
                    module_path=None,
                )
                result[name] = config_entry

        return list(result.values())

    def load_from_package(self, package_path: Path) -> None:
        """Discover configs in a package.

        This is a convenience method that combines discovery with explicit registration loading.

        Args:
            package_path: Root path of the package
        """
        self.discover_configs(package_path)
