from pathlib import Path

import pytest
from pydantic import ValidationError

from unique_toolkit.language_model.model_costs import (
    MODEL_COSTS_FILE_ENV,
    calculate_invocation_cost_usd,
    load_model_cost_catalog,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage


def _write_catalog(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


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
def test_load_model_cost_catalog__rejects_unsupported_version(tmp_path: Path) -> None:
    """Purpose: Verify unsupported cost schemas fail explicitly.
    Why this matters: Silently interpreting a new schema could report incorrect spend.
    Setup summary: Write a version-two catalog and assert loading raises ValueError.
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

    with pytest.raises(ValueError, match="Unsupported model cost schema version: 2"):
        load_model_cost_catalog(path)


@pytest.mark.ai
def test_load_model_cost_catalog__rejects_malformed_model(tmp_path: Path) -> None:
    """Purpose: Verify incomplete price rows are rejected.
    Why this matters: A missing completion rate must not produce a partial estimate.
    Setup summary: Omit completion pricing and assert Pydantic validation fails.
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

    with pytest.raises(ValidationError):
        load_model_cost_catalog(path)


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
