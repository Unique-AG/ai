from typing import Any


class DomainObject:
    """Wraps a raw UniqueObject, providing attribute-style access and instance methods.

    Subclasses add async methods (modify, delete, etc.) that operate on the specific
    resource without requiring the caller to pass user_id/company_id every time.
    """

    def __init__(self, user_id: str, company_id: str, raw: Any) -> None:
        self._user_id = user_id
        self._company_id = company_id
        self._raw = raw

    # ------------------------------------------------------------------
    # Attribute delegation
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        try:
            raw = object.__getattribute__(self, "_raw")
            return raw[name]
        except (KeyError, TypeError, AttributeError):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

    def __repr__(self) -> str:
        try:
            raw = object.__getattribute__(self, "_raw")
            obj_id = raw.get("id", "N/A") if isinstance(raw, dict) else "N/A"
        except AttributeError:
            obj_id = "N/A"
        return f"{type(self).__name__}(id={obj_id!r})"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_raw(self, new_raw: Any) -> None:
        self._raw = new_raw

    @property
    def raw(self) -> Any:
        """Access the underlying raw UniqueObject."""
        return self._raw


class BaseManager:
    """Base class for all resource managers.

    Stores user_id and company_id once so individual method calls
    don't require them as arguments.
    """

    def __init__(self, user_id: str, company_id: str) -> None:
        self._user_id = user_id
        self._company_id = company_id
