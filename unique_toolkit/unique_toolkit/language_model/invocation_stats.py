"""Per-invocation LLM usage stats with model identity.

Lives in its own module (not ``schemas.py``) because it needs
``LanguageModelName`` from ``infos.py``, which itself imports from
``schemas.py``.
"""

from typing import Annotated, Self

from humps import camelize
from pydantic import BaseModel, BeforeValidator, ConfigDict

from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.model_costs import calculate_invocation_cost_usd
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

# `protected_namespaces=()` allows the `model_name` field name.
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    protected_namespaces=(),
)


def _normalize_model_name(value: object) -> object:
    """Canonicalize model_name: known names become the enum, customs stay str.

    Pydantic's smart union keeps string inputs as `str` even when they match a
    `LanguageModelName` value, so without this the same model could appear as
    enum or str depending on the caller.
    """
    if isinstance(value, str) and not isinstance(value, LanguageModelName):
        value = value.strip()
        if not value:
            raise ValueError("model_name must be a non-empty model name")
        try:
            return LanguageModelName(value)
        except ValueError:
            return value
    return value


def _validate_source(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("source must be a non-empty string")
    return value


ModelName = Annotated[LanguageModelName | str, BeforeValidator(_normalize_model_name)]
Source = Annotated[str, BeforeValidator(_validate_source)]


class LanguageModelInvocationStats(BaseModel):
    """Usage of a single LLM invocation, tied to the model that served it."""

    model_config = model_config

    model_name: ModelName
    token_usage: LanguageModelTokenUsage
    source: Source  # e.g. "main_loop", tool/evaluation/postprocessor name
    cost_usd: float | None = None

    @classmethod
    def from_usage(
        cls,
        model_name: LanguageModelName | str,
        token_usage: LanguageModelTokenUsage,
        source: str,
    ) -> Self:
        return cls(
            model_name=model_name,
            token_usage=token_usage,
            source=source,
            cost_usd=calculate_invocation_cost_usd(str(model_name), token_usage),
        )
