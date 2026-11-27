from importlib import import_module
from typing import Any


def install(
    module_globals: dict[str, Any],
    exports: dict[str, tuple[str, str]],
    *,
    optional: frozenset[str] = frozenset(),
) -> None:
    """Install PEP 562 `__getattr__`/`__dir__` that lazily resolve `exports`."""

    def __getattr__(name: str) -> Any:
        module_name = module_globals["__name__"]
        export = exports.get(name)
        if export is None:
            raise AttributeError(f"module {module_name!r} has no attribute {name!r}")
        try:
            value = getattr(import_module(export[0]), export[1])
        except ImportError:
            if name not in optional:
                raise
            raise AttributeError(
                f"module {module_name!r} has no attribute {name!r}"
            ) from None
        module_globals[name] = value
        return value

    def __dir__() -> list[str]:
        return sorted(set(module_globals) | set(module_globals["__all__"]))

    module_globals["__getattr__"] = __getattr__
    module_globals["__dir__"] = __dir__
