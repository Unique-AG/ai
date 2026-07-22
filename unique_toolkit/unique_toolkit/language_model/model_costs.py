"""Load model prices and calculate the USD cost of LLM invocations."""

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

MODEL_COSTS_FILE_ENV = "MODEL_COSTS_FILE"
_LITELLM_PREFIX = "litellm:"
_TOKENS_PER_MILLION = 1_000_000


class ModelCost(BaseModel):
    """Per-million-token prices for one language model."""

    model_config = ConfigDict(extra="forbid")

    input: float
    completion: float
    currency: str = Field(default="USD", min_length=1)


class ModelCostCatalog(BaseModel):
    """Versioned model-price catalog rendered by the platform Helm charts."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    cost_schema_version: int = Field(alias="costSchemaVersion")
    models: dict[str, ModelCost] = Field(min_length=1)


@lru_cache(maxsize=None)
def _load_model_cost_catalog(path: Path) -> ModelCostCatalog:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    catalog = ModelCostCatalog.model_validate(payload)
    if catalog.cost_schema_version != 1:
        raise ValueError(
            f"Unsupported model cost schema version: {catalog.cost_schema_version}"
        )
    return catalog


def load_model_cost_catalog(path: str | Path | None = None) -> ModelCostCatalog | None:
    """Load and cache the configured catalog, or return None when not configured."""

    configured_path = path or os.getenv(MODEL_COSTS_FILE_ENV)
    if configured_path is None or not str(configured_path).strip():
        return None
    return _load_model_cost_catalog(Path(configured_path))


def calculate_invocation_cost_usd(
    model_name: str,
    token_usage: LanguageModelTokenUsage,
    catalog: ModelCostCatalog | None = None,
) -> float | None:
    """Calculate invocation cost using prompt and completion token totals."""

    if token_usage.prompt_tokens is None or token_usage.completion_tokens is None:
        return None

    active_catalog = catalog if catalog is not None else load_model_cost_catalog()
    if active_catalog is None:
        return None

    normalized_model_name = str(model_name)
    model_cost = active_catalog.models.get(normalized_model_name)
    if model_cost is None and normalized_model_name.startswith(_LITELLM_PREFIX):
        model_cost = active_catalog.models.get(
            normalized_model_name.removeprefix(_LITELLM_PREFIX)
        )
    if model_cost is None:
        return None

    return (
        token_usage.prompt_tokens * model_cost.input
        + token_usage.completion_tokens * model_cost.completion
    ) / _TOKENS_PER_MILLION
