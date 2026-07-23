"""Load model prices and calculate the USD cost of LLM invocations."""

import logging
import os
import time
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

logger = logging.getLogger(f"toolkit.language_model.{__name__}")

MODEL_COSTS_FILE_ENV = "MODEL_COSTS_FILE"
_LITELLM_PREFIX = "litellm:"
_TOKENS_PER_MILLION = 1_000_000

# Safety-only bound on how long a process may keep a loaded catalog. Not the
# primary refresh mechanism — just ensures a long-lived worker eventually
# re-reads a remounted price sheet.
_CACHE_MAX_AGE_SECONDS = 5 * 60


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


_catalog_cache: dict[Path, tuple[ModelCostCatalog, float]] = {}


def _parse_model_cost_catalog(path: Path) -> ModelCostCatalog:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    catalog = ModelCostCatalog.model_validate(payload)
    if catalog.cost_schema_version != 1:
        raise ValueError(
            f"Unsupported model cost schema version: {catalog.cost_schema_version}"
        )
    return catalog


def _load_model_cost_catalog(path: Path) -> ModelCostCatalog:
    now = time.monotonic()
    cached = _catalog_cache.get(path)
    if cached is not None:
        catalog, loaded_at = cached
        if now - loaded_at < _CACHE_MAX_AGE_SECONDS:
            return catalog

    catalog = _parse_model_cost_catalog(path)
    _catalog_cache[path] = (catalog, now)
    return catalog


def load_model_cost_catalog(path: str | Path | None = None) -> ModelCostCatalog | None:
    """Load and cache the configured catalog, or return None when unavailable.

    Returns None when the catalog path is unset, or when the file cannot be
    read/parsed. Cost capture must never abort a successful LLM call over a
    missing or invalid price sheet.
    """

    configured_path = path or os.getenv(MODEL_COSTS_FILE_ENV)
    if configured_path is None or not str(configured_path).strip():
        return None
    try:
        return _load_model_cost_catalog(Path(configured_path))
    except Exception as exc:
        logger.warning(
            "Failed to load model cost catalog from %s: %s",
            configured_path,
            exc,
        )
        return None


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
