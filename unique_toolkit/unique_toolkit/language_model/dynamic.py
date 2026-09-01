"""API-backed dynamic StrEnum utilities for tenant-scoped language models."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any, Literal

import unique_sdk
from pydantic import BaseModel
from unique_sdk.api_resources._llm_models import LLMModels

from unique_toolkit._common.async_ttl_cache import AsyncTTLCache
from unique_toolkit.language_model.enum_narrowing import (
    NoModelIntersectionError,
    build_language_model_enum_from_names,
    resolve_default_active_language_model,
)
from unique_toolkit.language_model.infos import LanguageModelName

logger = logging.getLogger(__name__)

ModelSource = Literal["unique_ai", "general"]

_DUMMY_SDK_VALUES = frozenset(
    {
        "",
        "dummy",
        "dummy_key",
        "dummy_id",
        "dummy_company_id",
        "dummy_user_id",
    }
)

_UNIQUE_AI_LLM_MODULE = "UNIQUE_AI"
_DYNAMIC_ENUM_RETRIEVAL_USER_ID = "dynamic_enum_retrieval"

_ACTIVE_MODEL_CACHE_TTL_MS = 5 * 60 * 1000
_async_active_model_cache = AsyncTTLCache(
    maxsize=1024, ttl_ms=_ACTIVE_MODEL_CACHE_TTL_MS
)


class ActiveLanguageModelConfigurationError(RuntimeError):
    """Raised when tenant-scoped language models cannot be resolved safely."""


def ensure_sdk_initialized() -> None:
    """Verify global unique_sdk credentials were configured before API calls."""
    if not unique_sdk.api_key or unique_sdk.api_key in _DUMMY_SDK_VALUES:
        raise ActiveLanguageModelConfigurationError(
            "unique_sdk.api_key is missing or unset. "
            "Initialize the SDK via UniqueSettings.init_sdk() or settings.init_sdk()."
        )
    if not unique_sdk.api_base:
        raise ActiveLanguageModelConfigurationError(
            "unique_sdk.api_base is missing. "
            "Initialize the SDK via UniqueSettings.init_sdk() or settings.init_sdk()."
        )
    if not unique_sdk.app_id or unique_sdk.app_id in _DUMMY_SDK_VALUES:
        raise ActiveLanguageModelConfigurationError(
            "unique_sdk.app_id is missing or unset. "
            "Initialize the SDK via UniqueSettings.init_sdk() or settings.init_sdk()."
        )


def ensure_company_id(company_id: str) -> str:
    """Validate tenant id before calling company-scoped model APIs."""
    normalized = company_id.strip()
    if not normalized or normalized in _DUMMY_SDK_VALUES:
        raise ActiveLanguageModelConfigurationError(
            "company_id is required to fetch active language models."
        )
    return normalized


def _dedupe_model_names(models: list[str]) -> list[str]:
    return list(dict.fromkeys(models))


def _log_unique_ai_fallback() -> None:
    logger.warning(
        "UNIQUE_AI model list is empty; falling back to general model listing. "
        + "Check UNIQUEAI_ALLOWED_MODELS on node-chat and that allowlisted model "
        + "keys match cluster deployments."
    )


def _active_model_cache_key(
    company_id: str, model_source: ModelSource, user_id: str
) -> str:
    return f"{company_id}:{model_source}:{user_id}"


async def _fetch_tenant_model_names_async(
    company_id: str,
    *,
    model_source: ModelSource,
    user_id: str = _DYNAMIC_ENUM_RETRIEVAL_USER_ID,
) -> list[str]:
    if model_source == "general":
        response = await LLMModels.get_models_async(
            user_id=user_id,
            company_id=company_id,
        )
        return _dedupe_model_names(response.get("models", []))

    unique_ai_response = await LLMModels.get_models_async(
        user_id=user_id,
        company_id=company_id,
        module=_UNIQUE_AI_LLM_MODULE,
    )
    unique_ai_models = _dedupe_model_names(unique_ai_response.get("models", []))
    if unique_ai_models:
        return unique_ai_models

    _log_unique_ai_fallback()
    general_response = await LLMModels.get_models_async(
        user_id=user_id,
        company_id=company_id,
    )
    return _dedupe_model_names(general_response.get("models", []))


def _build_active_language_model_enum(
    company_id: str,
    api_models: list[str],
    *,
    model_source: ModelSource,
) -> type[StrEnum]:
    try:
        return build_language_model_enum_from_names(api_models)
    except NoModelIntersectionError as exc:
        msg = (
            "No active language models intersect with LanguageModelName for company "
            f"{company_id} and model_source {model_source}. models={exc.models!r}"
        )
        logger.error(msg)
        raise ActiveLanguageModelConfigurationError(msg) from exc


async def _fetch_active_language_model_enum_async(
    company_id: str,
    *,
    model_source: ModelSource,
    user_id: str = _DYNAMIC_ENUM_RETRIEVAL_USER_ID,
) -> type[StrEnum]:
    ensure_sdk_initialized()
    try:
        api_models = await _fetch_tenant_model_names_async(
            company_id,
            model_source=model_source,
            user_id=user_id,
        )
    except Exception as exc:
        msg = f"Failed to fetch active language models for company {company_id}"
        logger.exception(msg)
        raise ActiveLanguageModelConfigurationError(msg) from exc

    return _build_active_language_model_enum(
        company_id,
        api_models,
        model_source=model_source,
    )


async def get_active_language_models_async(
    company_id: str,
    *,
    model_source: ModelSource,
    user_id: str = _DYNAMIC_ENUM_RETRIEVAL_USER_ID,
) -> type[StrEnum]:
    """Return a StrEnum subclass narrowed to models available for the tenant.

    Args:
        company_id: Tenant id passed to the node-chat models API.
        model_source: Which node-chat listing to use:

            - ``unique_ai``: ``module=UNIQUE_AI`` allowlisted models
            - ``general``: unfiltered cluster + custom models
        user_id: Passed to the models API; defaults to a fixed sentinel for
            dynamic enum retrieval (not a real end-user id).
    """
    company_id = ensure_company_id(company_id)
    enum_type, _from_cache = await _async_active_model_cache.get_or_fetch(
        _active_model_cache_key(company_id, model_source, user_id),
        lambda: _fetch_active_language_model_enum_async(
            company_id,
            model_source=model_source,
            user_id=user_id,
        ),
    )
    return enum_type


async def get_default_active_language_model_async(
    company_id: str,
    *,
    user_id: str = _DYNAMIC_ENUM_RETRIEVAL_USER_ID,
) -> LanguageModelName:
    """Return the preferred default model for *company_id*'s active set."""
    active_models = await get_active_language_models_async(
        company_id,
        model_source="unique_ai",
        user_id=user_id,
    )
    return resolve_default_active_language_model(active_models)


_LANGUAGE_MODEL_NAME_REF = "#/$defs/LanguageModelName"


def _narrow_language_model_enums(
    schema: dict[str, Any],
    active_model_names: set[str],
) -> None:
    """Filter the shared ``LanguageModelName`` enum def to the active set.

    JSON-schema ``$defs`` are shared by ``$ref``, so narrowing the single
    ``LanguageModelName`` enum narrows every field that references it at once
    — including bare-enum fields and models nested inside containers, which a
    field-by-field model rebuild would miss. The original enum order is
    preserved (stable, not API response order).
    """
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        return
    language_model_def = defs.get("LanguageModelName")
    if not isinstance(language_model_def, dict):
        return
    enum_values = language_model_def.get("enum")
    if not isinstance(enum_values, list):
        return
    language_model_def["enum"] = [
        value for value in enum_values if value in active_model_names
    ]


def _schema_references_language_model(prop_schema: dict[str, Any]) -> bool:
    ref = prop_schema.get("$ref")
    if ref == _LANGUAGE_MODEL_NAME_REF:
        return True

    any_of = prop_schema.get("anyOf")
    if not isinstance(any_of, list):
        return False

    return any(
        isinstance(branch, dict) and branch.get("$ref") == _LANGUAGE_MODEL_NAME_REF
        for branch in any_of
    )


def _referenced_schema(
    defs: Any,
    prop_schema: dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(defs, dict):
        return None

    ref = prop_schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        ref_schema = defs.get(ref.rsplit("/", 1)[-1])
        return ref_schema if isinstance(ref_schema, dict) else None

    any_of = prop_schema.get("anyOf")
    if not isinstance(any_of, list):
        return None
    for branch in any_of:
        if not isinstance(branch, dict):
            continue
        ref = branch.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            ref_schema = defs.get(ref.rsplit("/", 1)[-1])
            return ref_schema if isinstance(ref_schema, dict) else None
    return None


def _rewrite_language_model_default_value(
    defs: Any,
    prop_schema: dict[str, Any],
    value: Any,
    *,
    active_model_names: set[str],
    replacement_default: str,
) -> Any:
    if (
        isinstance(value, str)
        and value not in active_model_names
        and _schema_references_language_model(prop_schema)
    ):
        return replacement_default

    if not isinstance(value, dict):
        return value

    ref_schema = _referenced_schema(defs, prop_schema)
    if ref_schema is None:
        return value

    ref_properties = ref_schema.get("properties")
    if not isinstance(ref_properties, dict):
        return value

    for child_name, child_schema in ref_properties.items():
        if child_name not in value or not isinstance(child_schema, dict):
            continue
        value[child_name] = _rewrite_language_model_default_value(
            defs,
            child_schema,
            value[child_name],
            active_model_names=active_model_names,
            replacement_default=replacement_default,
        )
    return value


def _rewrite_language_model_property_defaults(
    defs: Any,
    properties: Any,
    *,
    active_model_names: set[str],
    replacement_default: str,
) -> None:
    if not isinstance(properties, dict):
        return
    for prop_schema in properties.values():
        if not isinstance(prop_schema, dict):
            continue
        if "default" not in prop_schema:
            continue
        prop_schema["default"] = _rewrite_language_model_default_value(
            defs,
            prop_schema,
            prop_schema.get("default"),
            active_model_names=active_model_names,
            replacement_default=replacement_default,
        )


def _rewrite_invalid_language_model_defaults(
    schema: dict[str, Any],
    *,
    active_model_names: set[str],
    replacement_default: str,
) -> None:
    """Rewrite stale language-model defaults in a narrowed JSON schema.

    Narrowing the enum leaves field defaults untouched, so a default can still
    point at a model no longer in the active set (including inside nested model
    instance defaults). Replace those with a deterministic in-set default.
    """
    defs = schema.get("$defs")

    _rewrite_language_model_property_defaults(
        defs,
        schema.get("properties"),
        active_model_names=active_model_names,
        replacement_default=replacement_default,
    )

    if not isinstance(defs, dict):
        return
    for def_schema in defs.values():
        if isinstance(def_schema, dict):
            _rewrite_language_model_property_defaults(
                defs,
                def_schema.get("properties"),
                active_model_names=active_model_names,
                replacement_default=replacement_default,
            )


def get_schema_with_available_language_models(
    model: type[BaseModel],
    available_models: list[str],
) -> dict[str, Any]:
    """Return a JSON schema whose language-model fields are narrowed to *available_models*.

    Operates directly on the generated JSON schema (the schema is the only
    deliverable): the shared ``LanguageModelName`` enum is filtered in place —
    narrowing every referencing field at once — and stale defaults are
    rewritten to a deterministic in-set default.

    Note: the ``LMI`` input type also carries a free-form "Language Model
    String" branch that is left unconstrained here (matching prior behavior);
    runtime enforcement of the tenant set belongs to ``build_lmi_annotation``.
    """
    if not available_models:
        return model.model_json_schema()

    active_model_enum = build_language_model_enum_from_names(available_models)
    active_model_names = {member.value for member in active_model_enum}

    schema = model.model_json_schema()
    _narrow_language_model_enums(schema, active_model_names)
    _rewrite_invalid_language_model_defaults(
        schema,
        active_model_names=active_model_names,
        replacement_default=resolve_default_active_language_model(
            active_model_enum
        ).value,
    )
    return schema


def clear_active_language_model_caches() -> None:
    """Clear in-process caches — intended for tests."""
    _async_active_model_cache.clear()
