"""Secret unwrapping helpers shared by proxy settings consumers."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import SecretStr


def read_secret(value: str | SecretStr | None) -> str:
    """Unwrap a secret or plain value to its string (empty string for ``None``)."""
    if value is None:
        return ""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value


def read_secret_mapping(
    headers: Mapping[str, str | SecretStr],
) -> dict[str, str]:
    """Unwrap a mapping of secret or plain header values."""
    return {name: read_secret(value) for name, value in headers.items()}
