from pathlib import Path

import pytest

from unique_toolkit.language_model import model_costs as model_costs_module
from unique_toolkit.language_model.model_costs import (
    MODEL_COSTS_FILE_ENV,
    calculate_invocation_cost_usd,
    load_model_cost_catalog,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage


def _write_catalog(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clear_catalog_cache() -> None:
    model_costs_module._catalog_cache.clear()
    yield
    model_costs_module._catalog_cache.clear()


@pytest.mark.ai
def test_load_model_cost_catalog__parses_supported_schema(tmp_path: Path) -> None:
    """Purpose: Verify schema-v1 catalogs are parsed into typed model prices.
    Why this matters: Helm-rendered pricing must be usable by runtime calculations.
    Setup summary: Write a minimal catalog, load it, and inspect its model entry.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
    completion: 8
""",
    )

    catalog = load_model_cost_catalog(path)

    assert catalog is not None
    assert catalog.models["test-model"].input == 2
    assert catalog.models["test-model"].currency == "USD"


@pytest.mark.ai
def test_load_model_cost_catalog__parses_optional_cache_pricing(tmp_path: Path) -> None:
    """Purpose: Verify cache-pricing fields rendered by the Helm chart parse.
    Why this matters: assistants-core and node-chat share a Helm template that
    renders cachedInput/cacheWrite/cacheWrite1h; unknown fields previously
    failed the whole catalog under extra="forbid", breaking cost tracking
    platform-wide, not just for models with cache pricing.
    Setup summary: Write a row with cache fields and assert they parse.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
    completion: 8
    cachedInput: 0.2
    cacheWrite: 2.5
    cacheWrite1h: 4
""",
    )

    catalog = load_model_cost_catalog(path)

    assert catalog is not None
    model_cost = catalog.models["test-model"]
    assert model_cost.cached_input == 0.2
    assert model_cost.cache_write == 2.5
    assert model_cost.cache_write_1h == 4


@pytest.mark.ai
def test_load_model_cost_catalog__cache_pricing_defaults_to_none(
    tmp_path: Path,
) -> None:
    """Purpose: Verify rows without cache pricing still parse.
    Why this matters: Most catalog rows omit cache fields entirely.
    Setup summary: Write a row without cache fields and assert they default to None.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
    completion: 8
""",
    )

    catalog = load_model_cost_catalog(path)

    assert catalog is not None
    model_cost = catalog.models["test-model"]
    assert model_cost.cached_input is None
    assert model_cost.cache_write is None
    assert model_cost.cache_write_1h is None


@pytest.mark.ai
def test_load_model_cost_catalog__parses_long_context_tier(tmp_path: Path) -> None:
    """Purpose: Verify the per-model long-context tier fields parse.
    Why this matters: node-chat renders longContextThreshold/InputMultiplier/
    CompletionMultiplier into the shared Helm ConfigMap; the toolkit must price
    the same tier so debug spend agrees with platform billing.
    Setup summary: Write a row with the three tier fields and assert they parse.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 5
    completion: 30
    longContextThreshold: 272000
    longContextInputMultiplier: 2
    longContextCompletionMultiplier: 1.5
""",
    )

    catalog = load_model_cost_catalog(path)

    assert catalog is not None
    model_cost = catalog.models["test-model"]
    assert model_cost.long_context_threshold == 272_000
    assert model_cost.long_context_input_multiplier == 2
    assert model_cost.long_context_completion_multiplier == 1.5


@pytest.mark.ai
def test_load_model_cost_catalog__long_context_tier_defaults_to_none(
    tmp_path: Path,
) -> None:
    """Purpose: Verify rows without a long-context tier still parse.
    Why this matters: Only 1.05M-context OpenAI models carry the tier today.
    Setup summary: Write a plain row and assert the tier fields default to None.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
    completion: 8
""",
    )

    catalog = load_model_cost_catalog(path)

    assert catalog is not None
    model_cost = catalog.models["test-model"]
    assert model_cost.long_context_threshold is None
    assert model_cost.long_context_input_multiplier is None
    assert model_cost.long_context_completion_multiplier is None


@pytest.mark.ai
@pytest.mark.parametrize(
    "partial_tier",
    [
        "    longContextThreshold: 272000\n",
        "    longContextInputMultiplier: 2\n    longContextCompletionMultiplier: 1.5\n",
    ],
)
def test_load_model_cost_catalog__rejects_partial_long_context_tier(
    tmp_path: Path, partial_tier: str
) -> None:
    """Purpose: Verify a partially defined long-context tier is rejected.
    Why this matters: Falling back to short-context rates for a row that declares
    a threshold would silently under-price every long request; "unknown" is the
    only safe outcome.
    Setup summary: Write a row with only some tier fields and assert loading
    returns None.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        f"""
costSchemaVersion: 1
models:
  test-model:
    input: 5
    completion: 30
{partial_tier}""",
    )

    assert load_model_cost_catalog(path) is None


@pytest.mark.ai
def test_load_model_cost_catalog__ignores_unknown_model_fields(tmp_path: Path) -> None:
    """Purpose: Verify a future, not-yet-modeled per-model field doesn't break loading.
    Why this matters: The Helm chart evolves independently of this schema; a single
    unknown field on one model row must not take down cost tracking for every model
    (this is exactly what happened before cachedInput/cacheWrite/cacheWrite1h were added).
    Setup summary: Write a row with an unrecognized field and assert it still loads.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
    completion: 8
    someFutureField: 1.5
""",
    )

    catalog = load_model_cost_catalog(path)

    assert catalog is not None
    assert catalog.models["test-model"].input == 2


@pytest.mark.ai
def test_load_model_cost_catalog__ignores_unknown_top_level_fields(
    tmp_path: Path,
) -> None:
    """Purpose: Verify a future, not-yet-modeled top-level catalog field doesn't
    break loading.
    Why this matters: Same resilience guarantee as per-model fields, at the
    catalog-envelope level.
    Setup summary: Write a catalog with an unrecognized top-level key.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
someFutureTopLevelField: true
models:
  test-model:
    input: 2
    completion: 8
""",
    )

    catalog = load_model_cost_catalog(path)

    assert catalog is not None
    assert catalog.models["test-model"].input == 2


@pytest.mark.ai
def test_load_model_cost_catalog__returns_none_for_unsupported_version(
    tmp_path: Path,
) -> None:
    """Purpose: Verify unsupported cost schemas are treated as unavailable.
    Why this matters: Cost capture must not abort LLM flows over a schema bump.
    Setup summary: Write a version-two catalog and assert loading returns None.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 2
models:
  test-model:
    input: 2
    completion: 8
""",
    )

    assert load_model_cost_catalog(path) is None


@pytest.mark.ai
def test_load_model_cost_catalog__returns_none_for_malformed_model(
    tmp_path: Path,
) -> None:
    """Purpose: Verify incomplete price rows are treated as unavailable.
    Why this matters: A missing completion rate must not abort cost capture.
    Setup summary: Omit completion pricing and assert loading returns None.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
""",
    )

    assert load_model_cost_catalog(path) is None


@pytest.mark.ai
def test_load_model_cost_catalog__returns_none_for_missing_file(tmp_path: Path) -> None:
    """Purpose: Verify a missing price sheet is treated as unavailable.
    Why this matters: Remount gaps must not abort UniqueAI after a successful LLM call.
    Setup summary: Point at a non-existent path and assert loading returns None.
    """
    assert load_model_cost_catalog(tmp_path / "missing-costs.yaml") is None


@pytest.mark.ai
def test_calculate_invocation_cost_usd__returns_none_when_catalog_load_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Purpose: Verify cost calculation soft-fails when the catalog cannot load.
    Why this matters: from_usage runs after successful LLM calls and must never raise.
    Setup summary: Point MODEL_COSTS_FILE at invalid YAML and assert cost is None.
    """
    path = _write_catalog(tmp_path / "costs.yaml", "not: valid: yaml: [")
    monkeypatch.setenv(MODEL_COSTS_FILE_ENV, str(path))

    cost = calculate_invocation_cost_usd(
        "test-model",
        LanguageModelTokenUsage(prompt_tokens=100, completion_tokens=20),
    )

    assert cost is None


@pytest.mark.ai
def test_load_model_cost_catalog__uses_environment_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Purpose: Verify deployment configuration selects the mounted price sheet.
    Why this matters: assistants-core supplies the catalog path through an env var.
    Setup summary: Set MODEL_COSTS_FILE and load without an explicit path.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
    completion: 8
""",
    )
    monkeypatch.setenv(MODEL_COSTS_FILE_ENV, str(path))

    catalog = load_model_cost_catalog()

    assert catalog is not None
    assert "test-model" in catalog.models


@pytest.mark.ai
def test_load_model_cost_catalog__reuses_cache_within_safety_ttl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Purpose: Verify catalog loads are cached until the safety TTL expires.
    Why this matters: Hot paths must not re-read YAML on every invocation.
    Setup summary: Load twice under a frozen clock and assert one parse.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
    completion: 8
""",
    )
    monkeypatch.setattr(model_costs_module.time, "monotonic", lambda: 100.0)
    parse_calls = {"count": 0}
    original_parse = model_costs_module._parse_model_cost_catalog

    def counting_parse(catalog_path: Path):
        parse_calls["count"] += 1
        return original_parse(catalog_path)

    monkeypatch.setattr(model_costs_module, "_parse_model_cost_catalog", counting_parse)

    first = load_model_cost_catalog(path)
    second = load_model_cost_catalog(path)

    assert first is second
    assert parse_calls["count"] == 1


@pytest.mark.ai
def test_load_model_cost_catalog__reloads_after_safety_ttl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Purpose: Verify the safety TTL forces a catalog re-read.
    Why this matters: Long-lived workers must eventually pick up remounted prices.
    Setup summary: Advance monotonic time past the max age and assert a reload.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
    completion: 8
""",
    )
    clock = {"now": 0.0}
    monkeypatch.setattr(model_costs_module.time, "monotonic", lambda: clock["now"])
    parse_calls = {"count": 0}
    original_parse = model_costs_module._parse_model_cost_catalog

    def counting_parse(catalog_path: Path):
        parse_calls["count"] += 1
        return original_parse(catalog_path)

    monkeypatch.setattr(model_costs_module, "_parse_model_cost_catalog", counting_parse)

    load_model_cost_catalog(path)
    clock["now"] = model_costs_module._CACHE_MAX_AGE_SECONDS
    load_model_cost_catalog(path)

    assert parse_calls["count"] == 2


@pytest.mark.ai
def test_calculate_invocation_cost_usd__prices_prompt_and_completion(
    tmp_path: Path,
) -> None:
    """Purpose: Verify invocation cost follows the platform per-million formula.
    Why this matters: Python debug spend must agree with node-chat accounting.
    Setup summary: Price known token counts and compare the resulting USD amount.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
    completion: 8
""",
    )
    catalog = load_model_cost_catalog(path)

    cost = calculate_invocation_cost_usd(
        "test-model",
        LanguageModelTokenUsage(prompt_tokens=1_000, completion_tokens=250),
        catalog,
    )

    assert cost == pytest.approx(0.004)


_SOL_CATALOG = """
costSchemaVersion: 1
models:
  AZURE_GPT_56_SOL_2026_0709:
    input: 5
    completion: 30
    longContextThreshold: 272000
    longContextInputMultiplier: 2
    longContextCompletionMultiplier: 1.5
  AZURE_GPT_56_TERRA_2026_0709:
    input: 2
    completion: 12
    longContextThreshold: 272000
    longContextInputMultiplier: 2
    longContextCompletionMultiplier: 1.5
  no-tier-model:
    input: 5
    completion: 30
"""


@pytest.mark.ai
@pytest.mark.parametrize(
    ("model_name", "input_rate", "completion_rate"),
    [
        ("AZURE_GPT_56_SOL_2026_0709", 5, 30),
        ("AZURE_GPT_56_TERRA_2026_0709", 2, 12),
    ],
)
def test_calculate_invocation_cost_usd__bills_base_rates_at_long_context_threshold(
    tmp_path: Path, model_name: str, input_rate: float, completion_rate: float
) -> None:
    """Purpose: Verify a request exactly at the threshold is priced short-context.
    Why this matters: OpenAI's rule is strictly "more than 272K"; 272,000 itself
    must not trigger the tier.
    Setup summary: Price exactly 272,000 prompt tokens and compare to base rates.
    """
    catalog = load_model_cost_catalog(_write_catalog(tmp_path / "c.yaml", _SOL_CATALOG))

    cost = calculate_invocation_cost_usd(
        model_name,
        LanguageModelTokenUsage(prompt_tokens=272_000, completion_tokens=1_000),
        catalog,
    )

    assert cost == pytest.approx((272_000 * input_rate + 1_000 * completion_rate) / 1e6)


@pytest.mark.ai
@pytest.mark.parametrize(
    ("model_name", "input_rate", "completion_rate"),
    [
        ("AZURE_GPT_56_SOL_2026_0709", 5, 30),
        ("AZURE_GPT_56_TERRA_2026_0709", 2, 12),
    ],
)
def test_calculate_invocation_cost_usd__reprices_entire_request_above_threshold(
    tmp_path: Path, model_name: str, input_rate: float, completion_rate: float
) -> None:
    """Purpose: Verify one token over the threshold re-prices the whole request.
    Why this matters: The long-context tier is a step function on the full
    request (2x input, 1.5x output), not a surcharge on the overflow.
    Setup summary: Price 272,001 prompt tokens and compare to multiplied rates.
    """
    catalog = load_model_cost_catalog(_write_catalog(tmp_path / "c.yaml", _SOL_CATALOG))

    cost = calculate_invocation_cost_usd(
        model_name,
        LanguageModelTokenUsage(prompt_tokens=272_001, completion_tokens=1_000),
        catalog,
    )

    assert cost == pytest.approx(
        (272_001 * input_rate * 2 + 1_000 * completion_rate * 1.5) / 1e6
    )


@pytest.mark.ai
def test_calculate_invocation_cost_usd__never_reprices_models_without_tier(
    tmp_path: Path,
) -> None:
    """Purpose: Verify models without a long-context tier keep flat pricing.
    Why this matters: The multiplier must be opt-in per model row, never implied.
    Setup summary: Price a huge prompt on an untiered row and compare to base rates.
    """
    catalog = load_model_cost_catalog(_write_catalog(tmp_path / "c.yaml", _SOL_CATALOG))

    cost = calculate_invocation_cost_usd(
        "no-tier-model",
        LanguageModelTokenUsage(prompt_tokens=1_000_000, completion_tokens=1_000),
        catalog,
    )

    assert cost == pytest.approx((1_000_000 * 5 + 1_000 * 30) / 1e6)


@pytest.mark.ai
def test_calculate_invocation_cost_usd__normalizes_litellm_prefix(
    tmp_path: Path,
) -> None:
    """Purpose: Verify toolkit model IDs resolve against node-chat price IDs.
    Why this matters: LanguageModelName prefixes LiteLLM routes with `litellm:`.
    Setup summary: Price an unprefixed catalog model using its prefixed runtime ID.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  anthropic-test:
    input: 3
    completion: 15
""",
    )
    catalog = load_model_cost_catalog(path)

    cost = calculate_invocation_cost_usd(
        "litellm:anthropic-test",
        LanguageModelTokenUsage(prompt_tokens=100, completion_tokens=20),
        catalog,
    )

    assert cost == pytest.approx(0.0006)


@pytest.mark.ai
@pytest.mark.parametrize(
    ("model_name", "usage"),
    [
        (
            "unknown-model",
            LanguageModelTokenUsage(prompt_tokens=100, completion_tokens=20),
        ),
        ("test-model", LanguageModelTokenUsage(total_tokens=120)),
    ],
)
def test_calculate_invocation_cost_usd__returns_none_when_price_is_unknown(
    tmp_path: Path,
    model_name: str,
    usage: LanguageModelTokenUsage,
) -> None:
    """Purpose: Verify incomplete pricing inputs remain explicitly unknown.
    Why this matters: Reporting zero would falsely classify unknown usage as free.
    Setup summary: Use a missing model or token split and assert the result is None.
    """
    path = _write_catalog(
        tmp_path / "costs.yaml",
        """
costSchemaVersion: 1
models:
  test-model:
    input: 2
    completion: 8
""",
    )
    catalog = load_model_cost_catalog(path)

    cost = calculate_invocation_cost_usd(model_name, usage, catalog)

    assert cost is None
