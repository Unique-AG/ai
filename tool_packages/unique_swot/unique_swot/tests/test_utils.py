from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_swot.utils import (
    SWOT_GENERATION,
    generate_structured_output,
)


class DummyOutput(BaseModel):
    value: str


def _build_llm(name: str = "dummy-model"):
    return SimpleNamespace(name=name, encoder_name="cl100k_base")


def _build_response(*, parsed: dict, usage: LanguageModelTokenUsage | None = None):
    message = Mock(parsed=parsed)
    response = Mock(choices=[Mock(message=message)])
    response.usage = usage
    return response


@pytest.mark.asyncio
async def test_generate_structured_output_retries_and_succeeds(monkeypatch):
    """Should retry failed calls and return the parsed structured model on success."""

    async def _raise_then_succeed(*_, **__):
        # First two attempts fail, third succeeds
        if call_counter["count"] < 2:
            call_counter["count"] += 1
            raise RuntimeError("temporary failure")
        return _build_response(parsed={"value": "ok"})

    call_counter = {"count": 0}
    llm_service = Mock()
    llm_service.complete_async = AsyncMock(side_effect=_raise_then_succeed)

    result = await generate_structured_output(
        user_message="hi",
        system_prompt="sys",
        llm=_build_llm(),
        output_model=DummyOutput,
        llm_service=llm_service,
    )

    assert isinstance(result, DummyOutput)
    assert result.value == "ok"
    assert llm_service.complete_async.await_count == 3


@pytest.mark.asyncio
async def test_generate_structured_output_returns_none_after_max_retries():
    """Should return None after exhausting retries."""

    llm_service = Mock()
    llm_service.complete_async = AsyncMock(side_effect=RuntimeError("fail"))

    result = await generate_structured_output(
        user_message="hi",
        system_prompt="sys",
        llm=_build_llm(),
        output_model=DummyOutput,
        llm_service=llm_service,
    )

    assert result is None
    assert llm_service.complete_async.await_count == 3


@pytest.mark.asyncio
async def test_generate_structured_output__records_invocation_stats_on_success():
    invocation_stats: list[LanguageModelInvocationStats] = []
    usage = LanguageModelTokenUsage(
        prompt_tokens=10, completion_tokens=5, total_tokens=15
    )
    llm_service = Mock()
    llm_service.complete_async = AsyncMock(
        return_value=_build_response(parsed={"value": "ok"}, usage=usage)
    )

    result = await generate_structured_output(
        user_message="hi",
        system_prompt="sys",
        llm=_build_llm("generation-model"),
        output_model=DummyOutput,
        llm_service=llm_service,
        invocation_stats=invocation_stats,
        source=SWOT_GENERATION,
    )

    assert result is not None
    assert len(invocation_stats) == 1
    assert invocation_stats[0].model_name == "generation-model"
    assert invocation_stats[0].source == SWOT_GENERATION
    assert invocation_stats[0].token_usage == usage


@pytest.mark.asyncio
async def test_generate_structured_output__retry_skips_failed_attempts():
    invocation_stats: list[LanguageModelInvocationStats] = []
    usage = LanguageModelTokenUsage(
        prompt_tokens=1, completion_tokens=1, total_tokens=2
    )
    call_counter = {"count": 0}

    async def _raise_then_succeed(*_, **__):
        if call_counter["count"] < 2:
            call_counter["count"] += 1
            raise RuntimeError("temporary failure")
        return _build_response(parsed={"value": "ok"}, usage=usage)

    llm_service = Mock()
    llm_service.complete_async = AsyncMock(side_effect=_raise_then_succeed)

    result = await generate_structured_output(
        user_message="hi",
        system_prompt="sys",
        llm=_build_llm(),
        output_model=DummyOutput,
        llm_service=llm_service,
        invocation_stats=invocation_stats,
        source=SWOT_GENERATION,
    )

    assert result is not None
    assert len(invocation_stats) == 1
    assert llm_service.complete_async.await_count == 3


@pytest.mark.asyncio
async def test_generate_structured_output__mixed_models_preserved():
    invocation_stats: list[LanguageModelInvocationStats] = []
    llm_service = Mock()

    async def _complete(*_, model_name: str, **__):
        usage = LanguageModelTokenUsage(
            prompt_tokens=1, completion_tokens=1, total_tokens=2
        )
        return _build_response(parsed={"value": "ok"}, usage=usage)

    llm_service.complete_async = AsyncMock(side_effect=_complete)

    await generate_structured_output(
        user_message="hi",
        system_prompt="sys",
        llm=_build_llm("model-a"),
        output_model=DummyOutput,
        llm_service=llm_service,
        invocation_stats=invocation_stats,
        source=SWOT_GENERATION,
    )
    await generate_structured_output(
        user_message="hi",
        system_prompt="sys",
        llm=_build_llm("model-b"),
        output_model=DummyOutput,
        llm_service=llm_service,
        invocation_stats=invocation_stats,
        source=SWOT_GENERATION,
    )

    assert [entry.model_name for entry in invocation_stats] == ["model-a", "model-b"]
