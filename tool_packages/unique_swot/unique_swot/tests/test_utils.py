from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

from unique_swot.utils import generate_structured_output


class DummyOutput(BaseModel):
    value: str


def _build_llm():
    # Minimal LMI-like object with the encoder name used by tiktoken
    return SimpleNamespace(name="dummy-model", encoder_name="cl100k_base")


@pytest.mark.asyncio
async def test_generate_structured_output_retries_and_succeeds(monkeypatch):
    """Should retry failed calls and return the parsed structured model on success."""

    async def _raise_then_succeed(*_, **__):
        # First two attempts fail, third succeeds
        if call_counter["count"] < 2:
            call_counter["count"] += 1
            raise RuntimeError("temporary failure")
        message = Mock(parsed={"value": "ok"})
        return Mock(choices=[Mock(message=message)])

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
