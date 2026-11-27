"""Project memory in the system prompt of project chats (UN-29145)."""

from __future__ import annotations

from logging import Logger
from unittest.mock import AsyncMock, MagicMock

import pytest
from jinja2 import ChainableUndefined
from jinja2.sandbox import SandboxedEnvironment
from unique_toolkit.language_model.default_language_model import DEFAULT_LANGUAGE_MODEL
from unique_toolkit.language_model.infos import LanguageModelInfo

from unique_orchestrator.config import UniqueAIPromptConfig
from unique_orchestrator.project_memory import (
    PROJECT_MEMORY_MAX_TOKENS,
    load_project_memory_text,
    project_memory_token_budget,
)

DOCUMENT = "# Project memory\n\n## Decisions\n- Ship the Q4 rollout in two waves.\n"


MODEL = LanguageModelInfo.from_name(DEFAULT_LANGUAGE_MODEL)


def _small_model(input_tokens: int) -> LanguageModelInfo:
    model = MODEL.model_copy(deep=True)
    model.token_limits.token_limit_input = input_tokens
    return model


def _event(project_id: str | None) -> MagicMock:
    event = MagicMock()
    event.payload.project_id = project_id
    event.user_id = "user_1"
    event.company_id = "company_1"
    return event


@pytest.mark.ai
@pytest.mark.asyncio
async def test_no_project_memory_outside_a_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk = AsyncMock()
    monkeypatch.setattr("unique_sdk.ProjectMemory.retrieve_async", sdk)

    text = await load_project_memory_text(
        event=_event(None), logger=MagicMock(), language_model=MODEL
    )

    assert text == ""
    sdk.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_project_chat_loads_the_document_as_the_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk = AsyncMock(return_value={"document": DOCUMENT, "state": "{}"})
    monkeypatch.setattr("unique_sdk.ProjectMemory.retrieve_async", sdk)

    text = await load_project_memory_text(
        event=_event("custom_space_1"), logger=MagicMock(), language_model=MODEL
    )

    assert text == DOCUMENT.strip()
    sdk.assert_awaited_once_with("user_1", "company_1", "custom_space_1")


@pytest.mark.ai
@pytest.mark.asyncio
async def test_a_failed_read_runs_the_turn_without_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Forbidden(Exception):
        pass

    monkeypatch.setattr(
        "unique_sdk.ProjectMemory.retrieve_async",
        AsyncMock(side_effect=Forbidden("projects are not enabled for user u-secret")),
    )
    logger = MagicMock(spec=Logger)

    text = await load_project_memory_text(
        event=_event("custom_space_1"), logger=logger, language_model=MODEL
    )

    assert text == ""
    logger.warning.assert_called_once()
    # Only the error type is logged, never its message.
    args = logger.warning.call_args.args
    assert "Forbidden" in args
    assert not any("u-secret" in str(a) for a in args)


@pytest.mark.ai
def test_budget_is_the_job_cap_or_a_quarter_of_the_model_input() -> None:
    assert project_memory_token_budget(_small_model(1_000_000)) == (
        PROJECT_MEMORY_MAX_TOKENS
    )
    assert project_memory_token_budget(_small_model(3_276)) == 819


@pytest.mark.ai
@pytest.mark.asyncio
async def test_an_oversized_memory_is_cut_to_the_model_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A small-context model must not get a memory larger than its share.
    lines = [
        f"- Decision {i}: ship wave {i} after review secret-{i}." for i in range(400)
    ]
    document = "# Project memory\n\n## Decisions\n" + "\n".join(lines)
    monkeypatch.setattr(
        "unique_sdk.ProjectMemory.retrieve_async",
        AsyncMock(return_value={"document": document}),
    )
    model = _small_model(800)
    logger = MagicMock(spec=Logger)

    text = await load_project_memory_text(
        event=_event("custom_space_1"), logger=logger, language_model=model
    )

    assert text.startswith("# Project memory")
    assert "Decision 0:" in text
    assert "Decision 399:" not in text
    assert "truncated" in text
    logger.warning.assert_called_once()
    # Only token counts are logged, never memory content.
    assert not any("secret" in str(a) for a in logger.warning.call_args.args)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_a_tokenizer_error_runs_the_turn_without_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "unique_sdk.ProjectMemory.retrieve_async",
        AsyncMock(return_value={"document": "- note <|endoftext|> secret-1"}),
    )
    monkeypatch.setattr(
        "unique_orchestrator.project_memory.enforce_token_cap",
        MagicMock(side_effect=ValueError("disallowed special token secret-1")),
    )
    logger = MagicMock(spec=Logger)

    text = await load_project_memory_text(
        event=_event("custom_space_1"), logger=logger, language_model=MODEL
    )

    assert text == ""
    args = logger.warning.call_args.args
    assert "ValueError" in args
    assert not any("secret" in str(a) for a in args)


def _render_default(**values: object) -> str:
    # Other context variables are irrelevant here; let them render empty.
    template = UniqueAIPromptConfig().system_prompt_template
    env = SandboxedEnvironment(undefined=ChainableUndefined)
    return env.from_string(template).render(**values)


@pytest.mark.ai
def test_default_system_prompt_includes_project_memory() -> None:
    prompt = _render_default(project_memory=DOCUMENT.strip())

    assert "# What I know about this project" in prompt
    assert "Ship the Q4 rollout in two waves." in prompt


@pytest.mark.ai
@pytest.mark.parametrize("project_memory", ["", None])
def test_default_system_prompt_has_no_section_without_memory(
    project_memory: str | None,
) -> None:
    prompt = _render_default(project_memory=project_memory)

    assert "What I know about this project" not in prompt
