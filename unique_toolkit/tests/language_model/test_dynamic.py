"""Tests for API-backed dynamic language model utilities."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, create_model
from pytest_mock import MockerFixture

from unique_toolkit._common.validators import (
    LMI,
    build_lmi_annotation,
    get_LMI_default_field,
)
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.dynamic import (
    ActiveLanguageModelConfigurationError,
    clear_active_language_model_caches,
    ensure_sdk_initialized,
    get_active_language_models_async,
    get_default_active_language_model_async,
    get_schema_with_available_language_models,
)
from unique_toolkit.language_model.enum_narrowing import (
    NoModelIntersectionError,
    build_language_model_enum_from_names,
    build_narrowed_language_model_enum,
    intersect_with_language_model_name,
    resolve_default_active_language_model,
)
from unique_toolkit.language_model.infos import LanguageModelName


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    clear_active_language_model_caches()


@pytest.fixture(autouse=True)
def _configured_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    import unique_sdk

    monkeypatch.setattr(unique_sdk, "api_key", "test-api-key", raising=False)
    monkeypatch.setattr(
        unique_sdk, "api_base", "http://localhost:8092/public", raising=False
    )
    monkeypatch.setattr(unique_sdk, "app_id", "test-app-id", raising=False)


class _TestLLMConfig(BaseModel):
    language_model: LMI = get_LMI_default_field(DEFAULT_GPT_4o)
    temperature: float = 0.7


class _NestedLLMConfig(BaseModel):
    small_model: LMI = get_LMI_default_field(DEFAULT_GPT_4o)
    label: str = "nested"


class _AssistantStyleConfig(BaseModel):
    large_model: LMI = get_LMI_default_field(DEFAULT_GPT_4o)
    nested: _NestedLLMConfig = _NestedLLMConfig()


class _EngineWithLMI(BaseModel):
    language_model: LMI = get_LMI_default_field(DEFAULT_GPT_4o)


class _EnginePlain(BaseModel):
    label: str = "plain"


class _UnionEngineConfig(BaseModel):
    engine: _EngineWithLMI | _EnginePlain


class _BareLanguageModelConfig(BaseModel):
    picked: LanguageModelName = DEFAULT_GPT_4o


class _ListLMIConfig(BaseModel):
    models: list[LMI] = []


def _build_lmi_test_model(available_models: list[str]) -> type[BaseModel]:
    narrowed_lmi = build_lmi_annotation(available_models)
    return create_model(
        "TestModel",
        language_model=(narrowed_lmi, get_LMI_default_field(DEFAULT_GPT_4o)),
    )


def _schema_enum_values(schema: dict[str, Any], field_name: str) -> list[str]:
    field_schema = schema["properties"][field_name]
    return _schema_enum_values_for_property(schema, field_schema)


def _schema_enum_values_for_property(
    schema: dict[str, Any],
    property_schema: dict[str, Any],
) -> list[str]:
    for variant in property_schema.get("anyOf", [property_schema]):
        if "enum" in variant:
            return variant["enum"]
        if "$ref" in variant:
            ref_name = variant["$ref"].rsplit("/", 1)[-1]
            ref_schema = schema["$defs"][ref_name]
            if "enum" in ref_schema:
                return ref_schema["enum"]
    raise AssertionError(f"No enum found in property schema: {property_schema}")


def _language_model_schema_variants(schema: dict[str, Any]) -> list[dict[str, Any]]:
    language_model_schema = schema["properties"]["language_model"]
    return language_model_schema.get("anyOf", [language_model_schema])


def _patch_llm_models_async(
    mocker: MockerFixture,
    *,
    unique_ai_models: list[str] | None = None,
    general_models: list[str] | None = None,
) -> Any:
    if general_models is None:
        general_models = unique_ai_models or []
    if unique_ai_models is None:
        unique_ai_models = general_models

    async def _side_effect(
        *,
        user_id: str,
        company_id: str,
        module: str | None = None,
    ) -> dict[str, list[str]]:
        if module == "UNIQUE_AI":
            return {"models": unique_ai_models}
        return {"models": general_models}

    return mocker.patch(
        "unique_toolkit.language_model.dynamic.LLMModels.get_models_async",
        side_effect=_side_effect,
    )


@pytest.mark.ai
async def test_get_active_language_models_async__intersection__returns_narrowed_enum(
    mocker: MockerFixture,
) -> None:
    _patch_llm_models_async(
        mocker,
        unique_ai_models=[
            "AZURE_GPT_4o_2024_1120",
            "AZURE_GPT_4o_MINI_2024_0718",
        ],
    )

    active_models = await get_active_language_models_async(
        "company-1",
        model_source="unique_ai",
    )

    assert set(active_models.__members__) == {
        "AZURE_GPT_4o_2024_1120",
        "AZURE_GPT_4o_MINI_2024_0718",
    }


@pytest.mark.ai
async def test_get_active_language_models_async__empty_intersection__raises(
    mocker: MockerFixture,
) -> None:
    _patch_llm_models_async(
        mocker,
        unique_ai_models=[],
        general_models=["UNKNOWN_MODEL"],
    )

    with pytest.raises(
        ActiveLanguageModelConfigurationError,
        match="company company-2 and model_source unique_ai.*UNKNOWN_MODEL",
    ):
        await get_active_language_models_async("company-2", model_source="unique_ai")


@pytest.mark.ai
async def test_get_active_language_models_async__api_error__raises(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "unique_toolkit.language_model.dynamic.LLMModels.get_models_async",
        side_effect=RuntimeError("API unavailable"),
    )

    with pytest.raises(ActiveLanguageModelConfigurationError, match="Failed to fetch"):
        await get_active_language_models_async("company-3", model_source="unique_ai")


@pytest.mark.ai
def test_ensure_sdk_initialized__dummy_api_key__raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import unique_sdk

    monkeypatch.setattr(unique_sdk, "api_key", "dummy_key", raising=False)

    with pytest.raises(ActiveLanguageModelConfigurationError, match="api_key"):
        ensure_sdk_initialized()


@pytest.mark.ai
async def test_get_active_language_models_async__missing_company_id__raises() -> None:
    with pytest.raises(ActiveLanguageModelConfigurationError, match="company_id"):
        await get_active_language_models_async("", model_source="unique_ai")


@pytest.mark.ai
async def test_get_active_language_models_async__cache_hit__skips_second_api_call(
    mocker: MockerFixture,
) -> None:
    get_models_async = _patch_llm_models_async(
        mocker,
        unique_ai_models=["AZURE_GPT_4o_2024_1120"],
    )

    await get_active_language_models_async("company-7", model_source="unique_ai")
    await get_active_language_models_async("company-7", model_source="unique_ai")

    assert get_models_async.call_count == 1


@pytest.mark.ai
async def test_get_active_language_models_async__cache_hit__normalizes_company_id_whitespace(
    mocker: MockerFixture,
) -> None:
    get_models_async = _patch_llm_models_async(
        mocker,
        unique_ai_models=["AZURE_GPT_4o_2024_1120"],
    )

    await get_active_language_models_async(" company-7 ", model_source="unique_ai")
    await get_active_language_models_async("company-7", model_source="unique_ai")

    assert get_models_async.call_count == 1


@pytest.mark.ai
def test_build_lmi_annotation__empty_list__uses_full_enum() -> None:
    TestModel = _build_lmi_test_model([])

    enum_values = _schema_enum_values(TestModel.model_json_schema(), "language_model")

    assert len(enum_values) == len(LanguageModelName.__members__)


@pytest.mark.ai
def test_build_lmi_annotation__invalid_models__raises() -> None:
    with pytest.raises(ValueError, match="No available language models"):
        build_lmi_annotation(["UNKNOWN_MODEL"])


@pytest.mark.ai
def test_get_schema_with_available_language_models__no_lmi_field__returns_unchanged_schema() -> (
    None
):
    class OtherConfig(BaseModel):
        temperature: float = 0.7

    schema = get_schema_with_available_language_models(
        OtherConfig,
        ["AZURE_GPT_4o_2024_1120"],
    )

    assert schema == OtherConfig.model_json_schema()
    assert "language_model" not in schema["properties"]


@pytest.mark.ai
def test_build_lmi_annotation__narrows_json_schema_enum() -> None:
    TestModel = _build_lmi_test_model(["AZURE_GPT_4o_2024_1120"])

    enum_values = _schema_enum_values(TestModel.model_json_schema(), "language_model")

    assert enum_values == ["AZURE_GPT_4o_2024_1120"]


@pytest.mark.ai
def test_build_lmi_annotation__narrowed_schema_removes_free_string_branch() -> None:
    TestModel = _build_lmi_test_model(["AZURE_GPT_4o_2024_1120"])

    variants = _language_model_schema_variants(TestModel.model_json_schema())

    assert {"type": "string", "title": "Language Model String"} not in variants


@pytest.mark.ai
def test_build_lmi_annotation__validation_rejects_unavailable_model() -> None:
    TestModel = _build_lmi_test_model(["AZURE_GPT_4o_2024_1120"])

    with pytest.raises(ValueError, match="not available for this tenant"):
        TestModel(language_model="AZURE_GPT_35_TURBO_0125")


@pytest.mark.ai
def test_get_schema_with_available_language_models__narrows_language_model_enum() -> (
    None
):
    schema = get_schema_with_available_language_models(
        _TestLLMConfig,
        ["AZURE_GPT_4o_2024_1120"],
    )

    enum_values = _schema_enum_values(schema, "language_model")

    assert enum_values == ["AZURE_GPT_4o_2024_1120"]
    assert schema["properties"]["temperature"]["default"] == 0.7


@pytest.mark.ai
def test_get_schema_with_available_language_models__narrows_all_lmi_fields() -> None:
    schema = get_schema_with_available_language_models(
        _AssistantStyleConfig,
        ["AZURE_GPT_35_TURBO_0125"],
    )

    assert _schema_enum_values(schema, "large_model") == ["AZURE_GPT_35_TURBO_0125"]

    nested_ref = schema["properties"]["nested"]["$ref"].rsplit("/", 1)[-1]
    nested_schema = schema["$defs"][nested_ref]
    assert _schema_enum_values_for_property(
        schema,
        nested_schema["properties"]["small_model"],
    ) == ["AZURE_GPT_35_TURBO_0125"]


@pytest.mark.ai
def test_get_schema_with_available_language_models__rewrites_invalid_defaults() -> None:
    schema = get_schema_with_available_language_models(
        _AssistantStyleConfig,
        ["AZURE_GPT_35_TURBO_0125"],
    )

    assert schema["properties"]["large_model"]["default"] == "AZURE_GPT_35_TURBO_0125"

    nested_ref = schema["properties"]["nested"]["$ref"].rsplit("/", 1)[-1]
    nested_schema = schema["$defs"][nested_ref]
    assert (
        nested_schema["properties"]["small_model"]["default"]
        == "AZURE_GPT_35_TURBO_0125"
    )
    assert schema["properties"]["nested"]["default"]["small_model"] == (
        "AZURE_GPT_35_TURBO_0125"
    )


@pytest.mark.ai
def test_get_schema_with_available_language_models__narrows_lmi_in_union_members() -> (
    None
):
    schema = get_schema_with_available_language_models(
        _UnionEngineConfig,
        ["AZURE_GPT_4o_2024_1120"],
    )

    engine_schema = schema["properties"]["engine"]
    variants = engine_schema.get("anyOf", [engine_schema])
    lmi_enums: list[list[str]] = []
    for variant in variants:
        ref = variant.get("$ref")
        if not isinstance(ref, str):
            continue
        ref_name = ref.rsplit("/", 1)[-1]
        ref_def = schema["$defs"][ref_name]
        language_model = ref_def.get("properties", {}).get("language_model")
        if not isinstance(language_model, dict):
            continue
        lmi_enums.append(
            _schema_enum_values_for_property(schema, language_model),
        )

    assert lmi_enums == [["AZURE_GPT_4o_2024_1120"]]


@pytest.mark.ai
def test_get_schema_with_available_language_models__narrows_bare_language_model_field() -> (
    None
):
    # A field typed as the bare ``LanguageModelName`` enum (not the ``LMI``
    # alias) shares the same ``$defs`` entry, so def-level narrowing reaches it
    # — the previous per-field model rebuild did not.
    schema = get_schema_with_available_language_models(
        _BareLanguageModelConfig,
        ["AZURE_GPT_35_TURBO_0125"],
    )

    assert _schema_enum_values(schema, "picked") == ["AZURE_GPT_35_TURBO_0125"]
    # Its now-unavailable default is rewritten to an in-set model.
    assert schema["properties"]["picked"]["default"] == "AZURE_GPT_35_TURBO_0125"


@pytest.mark.ai
def test_get_schema_with_available_language_models__narrows_lmi_inside_list() -> None:
    # LMI nested in a container references the shared enum def too, so it is
    # narrowed without the rebuild walking generic args.
    schema = get_schema_with_available_language_models(
        _ListLMIConfig,
        ["AZURE_GPT_35_TURBO_0125"],
    )

    assert schema["$defs"]["LanguageModelName"]["enum"] == ["AZURE_GPT_35_TURBO_0125"]
    item_schema = schema["properties"]["models"]["items"]
    assert _schema_enum_values_for_property(schema, item_schema) == [
        "AZURE_GPT_35_TURBO_0125"
    ]


@pytest.mark.ai
def test_intersect_with_language_model_name__no_match__raises() -> None:
    with pytest.raises(NoModelIntersectionError, match="UNKNOWN_MODEL") as exc_info:
        intersect_with_language_model_name(["UNKNOWN_MODEL"])

    assert exc_info.value.models == ["UNKNOWN_MODEL"]


@pytest.mark.ai
def test_build_narrowed_language_model_enum__empty_members__raises() -> None:
    with pytest.raises(NoModelIntersectionError, match="No available language models"):
        build_narrowed_language_model_enum({})


@pytest.mark.ai
def test_resolve_default_active_language_model__prefers_default_when_in_active_set() -> (
    None
):
    active_models = build_language_model_enum_from_names(
        ["AZURE_GPT_4o_MINI_2024_0718", DEFAULT_GPT_4o.name]
    )

    assert resolve_default_active_language_model(active_models) == DEFAULT_GPT_4o


@pytest.mark.ai
def test_resolve_default_active_language_model__uses_static_order_when_default_unavailable() -> (
    None
):
    active_models = build_language_model_enum_from_names(
        [
            "AZURE_GPT_4o_MINI_2024_0718",
            "AZURE_GPT_35_TURBO_0125",
        ]
    )

    assert resolve_default_active_language_model(active_models) == (
        LanguageModelName.AZURE_GPT_35_TURBO_0125
    )


@pytest.mark.ai
async def test_get_active_language_models_async__unique_ai_source__falls_back_to_general_when_empty(
    mocker: MockerFixture,
) -> None:
    _patch_llm_models_async(
        mocker,
        unique_ai_models=[],
        general_models=[
            "AZURE_GPT_4o_2024_1120",
            "AZURE_GPT_4o_MINI_2024_0718",
        ],
    )

    active_models = await get_active_language_models_async(
        "company-unique-ai-fallback",
        model_source="unique_ai",
    )

    assert set(active_models.__members__) == {
        "AZURE_GPT_4o_2024_1120",
        "AZURE_GPT_4o_MINI_2024_0718",
    }


@pytest.mark.ai
async def test_get_active_language_models_async__unique_ai_source__uses_allowlist_only(
    mocker: MockerFixture,
) -> None:
    _patch_llm_models_async(
        mocker,
        unique_ai_models=["AZURE_GPT_4o_2024_1120"],
        general_models=[
            "AZURE_GPT_4o_2024_1120",
            "AZURE_GPT_35_TURBO_0125",
            "litellm:gemini-2-5-pro",
        ],
    )

    active_models = await get_active_language_models_async(
        "company-allowlist",
        model_source="unique_ai",
    )

    assert set(active_models.__members__) == {"AZURE_GPT_4o_2024_1120"}


@pytest.mark.ai
async def test_get_active_language_models_async__general_source__uses_general_listing(
    mocker: MockerFixture,
) -> None:
    _patch_llm_models_async(
        mocker,
        unique_ai_models=["AZURE_GPT_4o_2024_1120"],
        general_models=[
            "AZURE_GPT_4o_2024_1120",
            "AZURE_GPT_35_TURBO_0125",
        ],
    )

    active_models = await get_active_language_models_async(
        "company-general",
        model_source="general",
    )

    assert set(active_models.__members__) == {
        "AZURE_GPT_4o_2024_1120",
        "AZURE_GPT_35_TURBO_0125",
    }


@pytest.mark.ai
async def test_get_default_active_language_model_async__uses_tenant_active_set(
    mocker: MockerFixture,
) -> None:
    _patch_llm_models_async(
        mocker,
        unique_ai_models=[
            "AZURE_GPT_4o_MINI_2024_0718",
            "AZURE_GPT_35_TURBO_0125",
        ],
    )

    default_model = await get_default_active_language_model_async("company-9")

    assert default_model == LanguageModelName.AZURE_GPT_35_TURBO_0125
