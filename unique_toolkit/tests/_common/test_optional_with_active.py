"""Tests for the OptionalWithActive pattern."""

from __future__ import annotations

from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic.optional_with_active import (
    OptionalWithActive,
    optional_with_active,
)


class CodeInterpreterConfig(BaseModel):
    """Example config for testing."""

    timeout: int = Field(default=30, description="Execution timeout in seconds")
    max_memory_mb: int = Field(default=512, description="Maximum memory in MB")
    allowed_packages: list[str] = Field(default_factory=list, description="Allowed packages")


class ExperimentalConfig(BaseModel):
    """Example parent config using the pattern."""

    code_interpreter: OptionalWithActive(CodeInterpreterConfig) = optional_with_active(
        CodeInterpreterConfig
    )


def test_active_false_returns_none() -> None:
    config = ExperimentalConfig.model_validate(
        {"code_interpreter": {"active": False, "timeout": 60, "max_memory_mb": 1024}}
    )
    assert config.code_interpreter is None


def test_active_true_returns_config() -> None:
    config = ExperimentalConfig.model_validate(
        {"code_interpreter": {"active": True, "timeout": 60, "max_memory_mb": 1024}}
    )
    assert config.code_interpreter is not None
    assert isinstance(config.code_interpreter, CodeInterpreterConfig)
    assert config.code_interpreter.timeout == 60
    assert config.code_interpreter.max_memory_mb == 1024


def test_null_input_returns_none() -> None:
    config = ExperimentalConfig.model_validate({"code_interpreter": None})
    assert config.code_interpreter is None


def test_backwards_compat_object_without_active_treated_as_active() -> None:
    config = ExperimentalConfig.model_validate({"code_interpreter": {"timeout": 45}})
    assert config.code_interpreter is not None
    assert config.code_interpreter.timeout == 45
    assert config.code_interpreter.max_memory_mb == 512


def test_can_construct_with_base_model_instance() -> None:
    config = ExperimentalConfig(code_interpreter=CodeInterpreterConfig(timeout=120))
    assert config.code_interpreter is not None
    assert config.code_interpreter.timeout == 120


def test_none_serializes_with_active_false_and_defaults() -> None:
    config = ExperimentalConfig(code_interpreter=None)
    dumped = config.model_dump()

    assert dumped["code_interpreter"]["active"] is False
    assert dumped["code_interpreter"]["timeout"] == 30
    assert dumped["code_interpreter"]["max_memory_mb"] == 512
    assert dumped["code_interpreter"]["allowed_packages"] == []


def test_config_serializes_with_active_true() -> None:
    config = ExperimentalConfig(
        code_interpreter=CodeInterpreterConfig(timeout=120, max_memory_mb=2048)
    )
    dumped = config.model_dump()

    assert dumped["code_interpreter"]["active"] is True
    assert dumped["code_interpreter"]["timeout"] == 120
    assert dumped["code_interpreter"]["max_memory_mb"] == 2048


def test_schema_contains_active_field_and_defaults() -> None:
    schema = ExperimentalConfig.model_json_schema()
    defs = schema["$defs"]
    active_schema = defs["CodeInterpreterConfigWithActive"]

    props = active_schema["properties"]
    assert props["active"]["type"] == "boolean"
    assert props["active"]["default"] is False
    assert props["timeout"]["default"] == 30
    assert props["max_memory_mb"]["default"] == 512
    assert props["allowed_packages"]["default"] == []

