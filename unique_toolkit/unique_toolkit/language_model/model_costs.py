"""Load model prices and calculate the USD cost of LLM invocations."""

import logging
import os
import time
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

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

    # Unknown fields are ignored, not rejected: the Helm-rendered schema evolves
    # independently of this one. Required fields below still validate strictly.
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    input: float
    completion: float
    currency: str = Field(default="USD", min_length=1)
    # Optional cache pricing rendered by the same Helm chart as node-chat's
    # cost-sheet.schema.json. Absent for rows without verified cache pricing yet.
    cached_input: float | None = Field(default=None, alias="cachedInput")
    cache_write: float | None = Field(default=None, alias="cacheWrite")
    cache_write_1h: float | None = Field(default=None, alias="cacheWrite1h")
    # Long-context tier (e.g. OpenAI GPT-5.x >272K input tokens): above the
    # threshold the ENTIRE request is billed at these multipliers, not just the
    # overflow. All three are required together; a partial definition is rejected
    # so a misconfigured row is never silently priced at short-context rates.
    long_context_threshold: int | None = Field(
        default=None, alias="longContextThreshold"
    )
    long_context_input_multiplier: float | None = Field(
        default=None, alias="longContextInputMultiplier"
    )
    long_context_completion_multiplier: float | None = Field(
        default=None, alias="longContextCompletionMultiplier"
    )

    @model_validator(mode="after")
    def _validate_long_context_all_or_none(self) -> "ModelCost":
        fields = (
            self.long_context_threshold,
            self.long_context_input_multiplier,
            self.long_context_completion_multiplier,
        )
        defined = [field for field in fields if field is not None]
        if defined and len(defined) != len(fields):
            raise ValueError(
                "longContextThreshold, longContextInputMultiplier and "
                "longContextCompletionMultiplier must be set together"
            )
        return self

    def multipliers_for(self, prompt_tokens: int) -> tuple[float, float]:
        """Return ``(input_multiplier, completion_multiplier)`` for a request.

        ``prompt_tokens`` is the provider-reported input size of the single
        request (for OpenAI this already includes cached tokens).
        """
        if (
            self.long_context_threshold is None
            or self.long_context_input_multiplier is None
            or self.long_context_completion_multiplier is None
            or prompt_tokens <= self.long_context_threshold
        ):
            return 1.0, 1.0
        return (
            self.long_context_input_multiplier,
            self.long_context_completion_multiplier,
        )


class ModelCostCatalog(BaseModel):
    """Versioned model-price catalog rendered by the platform Helm charts."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

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

    input_multiplier, completion_multiplier = model_cost.multipliers_for(
        token_usage.prompt_tokens
    )
    return (
        token_usage.prompt_tokens * model_cost.input * input_multiplier
        + token_usage.completion_tokens * model_cost.completion * completion_multiplier
    ) / _TOKENS_PER_MILLION
