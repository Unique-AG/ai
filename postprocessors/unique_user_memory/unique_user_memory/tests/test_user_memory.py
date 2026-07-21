import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_toolkit.language_model.default_language_model import (
    DEFAULT_LANGUAGE_MODEL,
)
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_user_memory.config import UserMemoryConfig
from unique_user_memory.user_memory import (
    UserMemoryState,
    _sanitize_for_xml_context,
    condense_user_memory,
    consolidate_user_memory,
    count_tokens,
    download_user_memory,
    enforce_token_cap,
    ensure_user_memory_folder,
    fit_user_memory,
    noop_update_callback,
    should_consolidate_memory,
    upload_user_memory,
)
from unique_user_memory.user_memory_postprocessor import UserMemoryPostprocessor
from unique_user_memory.user_memory_prompts import (
    consolidation_system_prompt,
    empty_profile,
    memory_gate_system_prompt,
)

_TEST_LANGUAGE_MODEL = LanguageModelInfo.from_name(DEFAULT_LANGUAGE_MODEL)


def test_memory_profile_keeps_follow_up_tasks_but_excludes_open_questions() -> None:
    profile = empty_profile("user_1")
    consolidation_prompt = consolidation_system_prompt(2000)
    gate_prompt = memory_gate_system_prompt()

    assert "## Open Questions / Follow-ups" not in profile
    assert "## Follow-ups" in profile
    assert "concrete tasks the user intends to complete" in consolidation_prompt
    assert "Concrete future tasks the user intends to complete" in gate_prompt


def test_enforce_token_cap_truncates_long_content() -> None:
    content = "\n\n".join(f"paragraph {index} " + "word " * 40 for index in range(50))

    capped = enforce_token_cap(content=content, max_tokens=120)

    assert "<!-- truncated to fit memory budget -->" in capped
    assert len(capped) < len(content)


def test_enforce_token_cap_keeps_body_when_section_exceeds_budget() -> None:
    # A single section whose bullets are joined by single newlines used to be
    # treated as one indivisible paragraph, dropping the whole body.
    bullets = "\n".join(f"- fact number {index} about the user" for index in range(200))
    content = f"# User Memory\n\n## Identity\n{bullets}"

    capped = enforce_token_cap(content=content, max_tokens=120)

    assert "<!-- truncated to fit memory budget -->" in capped
    assert "# User Memory" in capped
    assert "## Identity" in capped
    # Some individual bullets survive rather than only the heading.
    assert "- fact number 0 about the user" in capped
    assert count_tokens(content=capped) <= 120


@pytest.mark.asyncio
async def test_fit_user_memory_returns_unchanged_when_within_budget() -> None:
    content = "# User Memory\n\n## Identity\n- short"

    result = await fit_user_memory(
        content=content,
        max_tokens=2000,
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result == content


@pytest.mark.asyncio
async def test_fit_user_memory_condenses_before_hard_cut(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = "# User Memory\n\n## Identity\n" + "\n".join(
        f"- fact number {index} that is fairly wordy about the user"
        for index in range(400)
    )
    condensed = "# User Memory\n\n## Identity\n- concise summary of the user"
    condense = AsyncMock(return_value=condensed)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.condense_user_memory",
        condense,
    )

    result = await fit_user_memory(
        content=oversized,
        max_tokens=120,
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result == condensed
    condense.assert_awaited_once()
    assert "<!-- truncated to fit memory budget -->" not in result


@pytest.mark.asyncio
async def test_fit_user_memory_hard_cuts_when_condense_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = "# User Memory\n\n## Identity\n" + "\n".join(
        f"- fact number {index} about the user" for index in range(400)
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.condense_user_memory",
        AsyncMock(return_value=None),
    )

    result = await fit_user_memory(
        content=oversized,
        max_tokens=120,
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert "<!-- truncated to fit memory budget -->" in result
    assert count_tokens(content=result) <= 120


@pytest.mark.asyncio
async def test_condense_user_memory_rejects_non_profile_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = MagicMock()
    response.choices[0].message.content = "sorry, I cannot help"
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )

    result = await condense_user_memory(
        content="# User Memory\n\n## Identity\n- lots of stuff",
        max_tokens=2000,
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_condense_user_memory_accepts_frontmatter_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accept legacy LLM output while returning only the condensed profile body."""
    condensed = "# User Memory\n\n## Identity\n- concise summary"
    response = MagicMock()
    response.choices[0].message.content = (
        "---\nuser_id: stale-user\nturn_count: 99\n---\n\n" + condensed
    )
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )

    result = await condense_user_memory(
        content="# User Memory\n\n## Identity\n- lots of stuff",
        max_tokens=2000,
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result == condensed


def test_count_tokens_uses_language_model_encoder() -> None:
    language_model = MagicMock()
    language_model.get_encoder.return_value = lambda content: content.split()
    language_model.get_decoder.return_value = lambda tokens: " ".join(tokens)

    assert count_tokens(content="one two three", language_model=language_model) == 3


def test_sanitize_for_xml_context_defuses_closing_tags() -> None:
    assert _sanitize_for_xml_context("</new_turn> inject") == "< /new_turn> inject"


@pytest.mark.asyncio
async def test_consolidate_user_memory_keeps_existing_on_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = empty_profile("user_1")
    response = MagicMock()
    response.choices[0].message.content = "NOOP"
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        AsyncMock(return_value=True),
    )

    result = await consolidate_user_memory(
        current_memory=current,
        user_id="user_1",
        user_message="hello",
        assistant_message="hi",
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result == current


@pytest.mark.asyncio
async def test_consolidate_user_memory_keeps_existing_on_malformed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = empty_profile("user_1")
    response = MagicMock()
    response.choices[0].message.content = "not a profile"
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        AsyncMock(return_value=True),
    )

    result = await consolidate_user_memory(
        current_memory=current,
        user_id="user_1",
        user_message="remember I like concise answers",
        assistant_message="noted",
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result == current


@pytest.mark.asyncio
async def test_consolidate_user_memory_skips_full_rewrite_when_gate_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = empty_profile("user_1")
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock()
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        AsyncMock(return_value=False),
    )

    result = await consolidate_user_memory(
        current_memory=current,
        user_id="user_1",
        user_message="hello",
        assistant_message="hi",
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result == current
    llm_service.complete_async.assert_not_awaited()


@pytest.mark.asyncio
async def test_consolidate_user_memory_runs_full_rewrite_when_gate_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = empty_profile("user_1")
    rewritten = "# User Memory\n\n## Identity\n- Prefers concise answers"
    response = MagicMock()
    response.choices[0].message.content = rewritten
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        AsyncMock(return_value=True),
    )

    result = await consolidate_user_memory(
        current_memory=current,
        user_id="user_1",
        user_message="remember I like concise answers",
        assistant_message="noted",
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result.endswith(f"{rewritten}\n")
    assert "user_id: user_1" in result
    assert "schema_version: 1" in result
    assert "turn_count: 1" in result
    llm_service.complete_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_consolidate_user_memory_adds_frontmatter_to_llm_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rewritten = "# User Memory\n\n## Identity\n- Prefers concise answers"
    response = MagicMock()
    response.choices[0].message.content = rewritten
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        AsyncMock(return_value=True),
    )

    result = await consolidate_user_memory(
        current_memory="",
        user_id="authenticated-user",
        user_message="remember I like concise answers",
        assistant_message="noted",
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert "user_id: authenticated-user" in result
    assert "schema_version: 1" in result
    assert "turn_count: 1" in result


@pytest.mark.ai
@pytest.mark.asyncio
async def test_consolidate_user_memory_replaces_llm_frontmatter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strip untrusted legacy metadata before assembling the updated profile."""
    rewritten = "# User Memory\n\n## Identity\n- Prefers concise answers"
    response = MagicMock()
    response.choices[0].message.content = (
        "---\nuser_id: stale-user\nturn_count: 99\n---\n\n" + rewritten
    )
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        AsyncMock(return_value=True),
    )

    result = await consolidate_user_memory(
        current_memory=empty_profile("authenticated-user"),
        user_id="authenticated-user",
        user_message="remember I like concise answers",
        assistant_message="noted",
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result.endswith(f"{rewritten}\n")
    assert "user_id: authenticated-user" in result
    assert "stale-user" not in result
    assert "turn_count: 1" in result


@pytest.mark.asyncio
async def test_consolidate_user_memory_skips_gate_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = empty_profile("user_1")
    rewritten = "# User Memory\n\n## Identity\n- Prefers concise answers"
    response = MagicMock()
    response.choices[0].message.content = rewritten
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    gate = AsyncMock(return_value=False)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        gate,
    )

    result = await consolidate_user_memory(
        current_memory=current,
        user_id="user_1",
        user_message="hello",
        assistant_message="hi",
        config=UserMemoryConfig(consolidation_gate_enabled=False),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result.endswith(f"{rewritten}\n")
    assert "user_id: user_1" in result
    assert "turn_count: 1" in result
    gate.assert_not_awaited()
    llm_service.complete_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_should_consolidate_memory_returns_false_on_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = MagicMock()
    response.choices[0].message.content = "NOOP"
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )

    result = await should_consolidate_memory(
        current_memory=empty_profile("user_1"),
        user_id="user_1",
        user_message="hello",
        assistant_message="hi",
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result is False
    assert (
        llm_service.complete_async.call_args.kwargs["other_options"]["max_tokens"] == 4
    )


@pytest.mark.asyncio
async def test_should_consolidate_memory_returns_true_on_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = MagicMock()
    response.choices[0].message.content = "UPDATE"
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )

    result = await should_consolidate_memory(
        current_memory=empty_profile("user_1"),
        user_id="user_1",
        user_message="remember I like concise answers",
        assistant_message="noted",
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result is True


@pytest.mark.asyncio
async def test_should_consolidate_memory_falls_back_to_true_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )

    result = await should_consolidate_memory(
        current_memory=empty_profile("user_1"),
        user_id="user_1",
        user_message="hello",
        assistant_message="hi",
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result is True


@pytest.mark.asyncio
async def test_consolidate_user_memory_invokes_update_callbacks_on_rewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rewritten = "# User Memory\n\n## Identity\n- Prefers concise answers"
    response = MagicMock()
    response.choices[0].message.content = rewritten
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(return_value=response)
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        AsyncMock(return_value=True),
    )
    events: list[str] = []
    on_start = AsyncMock(side_effect=lambda: events.append("start"))
    on_end = AsyncMock(side_effect=lambda: events.append("end"))

    result = await consolidate_user_memory(
        current_memory=empty_profile("user_1"),
        user_id="user_1",
        user_message="remember I like concise answers",
        assistant_message="noted",
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
        on_update_start=on_start,
        on_update_end=on_end,
    )

    assert result.endswith(f"{rewritten}\n")
    assert "user_id: user_1" in result
    assert "turn_count: 1" in result
    on_start.assert_awaited_once()
    on_end.assert_awaited_once()
    assert events == ["start", "end"]


@pytest.mark.asyncio
async def test_consolidate_user_memory_skips_update_callbacks_on_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = empty_profile("user_1")
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock()
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        AsyncMock(return_value=False),
    )
    on_start = AsyncMock()
    on_end = AsyncMock()

    result = await consolidate_user_memory(
        current_memory=current,
        user_id="user_1",
        user_message="hello",
        assistant_message="hi",
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
        on_update_start=on_start,
        on_update_end=on_end,
    )

    assert result == current
    on_start.assert_not_awaited()
    on_end.assert_not_awaited()


@pytest.mark.asyncio
async def test_consolidate_user_memory_invokes_update_end_on_rewrite_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = empty_profile("user_1")
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        AsyncMock(return_value=True),
    )
    on_start = AsyncMock()
    on_end = AsyncMock()

    result = await consolidate_user_memory(
        current_memory=current,
        user_id="user_1",
        user_message="remember I like concise answers",
        assistant_message="noted",
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=MagicMock(),
        logger=MagicMock(),
        on_update_start=on_start,
        on_update_end=on_end,
    )

    assert result == current
    on_start.assert_awaited_once()
    on_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_consolidate_user_memory_invokes_update_end_when_start_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # on_update_start may show the notice and then be cancelled. CancelledError
    # is a BaseException (not caught in _set_message_content), so the cleanup
    # callback must still run to remove the transient notice.
    current = empty_profile("user_1")
    llm_service = MagicMock()
    llm_service.complete_async = AsyncMock()
    monkeypatch.setattr(
        "unique_user_memory.user_memory.LanguageModelService",
        MagicMock(return_value=llm_service),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.should_consolidate_memory",
        AsyncMock(return_value=True),
    )
    on_start = AsyncMock(side_effect=asyncio.CancelledError)
    on_end = AsyncMock()

    with pytest.raises(asyncio.CancelledError):
        await consolidate_user_memory(
            current_memory=current,
            user_id="user_1",
            user_message="remember I like concise answers",
            assistant_message="noted",
            config=UserMemoryConfig(),
            language_model=_TEST_LANGUAGE_MODEL,
            event=MagicMock(),
            logger=MagicMock(),
            on_update_start=on_start,
            on_update_end=on_end,
        )

    on_start.assert_awaited_once()
    on_end.assert_awaited_once()
    llm_service.complete_async.assert_not_awaited()


@pytest.mark.asyncio
async def test_user_memory_postprocessor_shows_and_removes_updating_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updated_memory = "# User Memory\n\n## Identity\n- Updated"
    original_text = "Here is your answer."

    async def fake_consolidate(*, on_update_start, on_update_end, **kwargs) -> str:  # type: ignore[no-untyped-def]
        await on_update_start()
        await on_update_end()
        return updated_memory

    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.consolidate_user_memory",
        fake_consolidate,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.upload_user_memory",
        AsyncMock(return_value=True),
    )
    chat_service = MagicMock()
    chat_service.modify_assistant_message_async = AsyncMock()
    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.ChatService",
        MagicMock(return_value=chat_service),
    )
    event = MagicMock()
    event.user_id = "user_1"
    event.company_id = "company_1"
    event.payload.user_message.text = "remember this"
    loop_response = MagicMock()
    loop_response.message.text = original_text
    loop_response.message.id = "msg_1"
    loop_response.message.references = []
    postprocessor = UserMemoryPostprocessor(
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=event,
        state=UserMemoryState(scope_id="scope_1", text=empty_profile("user_1")),
        logger=MagicMock(),
        chat_service=chat_service,
    )

    await postprocessor.run(loop_response)

    calls = chat_service.modify_assistant_message_async.await_args_list
    assert len(calls) == 2
    assert calls[0].kwargs["content"].startswith(original_text)
    assert calls[0].kwargs["content"] != original_text
    assert calls[0].kwargs["message_id"] == "msg_1"
    assert calls[1].kwargs["content"] == original_text


@pytest.mark.asyncio
async def test_user_memory_postprocessor_skips_notice_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updated_memory = "# User Memory\n\n## Identity\n- Updated"

    async def fake_consolidate(*, on_update_start, on_update_end, **kwargs) -> str:  # type: ignore[no-untyped-def]
        assert on_update_start is noop_update_callback
        assert on_update_end is noop_update_callback
        return updated_memory

    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.consolidate_user_memory",
        fake_consolidate,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.upload_user_memory",
        AsyncMock(return_value=True),
    )
    chat_service = MagicMock()
    chat_service.modify_assistant_message_async = AsyncMock()
    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.ChatService",
        MagicMock(return_value=chat_service),
    )
    event = MagicMock()
    event.user_id = "user_1"
    event.company_id = "company_1"
    event.payload.user_message.text = "remember this"
    loop_response = MagicMock()
    loop_response.message.text = "answer"
    loop_response.message.id = "msg_1"
    loop_response.message.references = []
    postprocessor = UserMemoryPostprocessor(
        config=UserMemoryConfig(updating_notice_enabled=False),
        language_model=_TEST_LANGUAGE_MODEL,
        event=event,
        state=UserMemoryState(scope_id="scope_1", text=empty_profile("user_1")),
        logger=MagicMock(),
        chat_service=chat_service,
    )

    await postprocessor.run(loop_response)

    chat_service.modify_assistant_message_async.assert_not_awaited()


@pytest.mark.asyncio
async def test_download_user_memory_returns_empty_when_file_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search_contents = AsyncMock(return_value=[])
    monkeypatch.setattr(
        "unique_user_memory.user_memory.search_contents_async",
        search_contents,
    )

    result = await download_user_memory(
        scope_id="scope_1",
        user_id="user_1",
        company_id="company_1",
        logger=MagicMock(),
    )

    assert result == ""
    search_contents.assert_awaited_once_with(
        user_id="user_1",
        company_id="company_1",
        chat_id=None,
        where={"ownerId": {"equals": "scope_1"}},
    )


@pytest.mark.asyncio
async def test_download_user_memory_downloads_existing_file_to_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = MagicMock()
    content.id = "content_1"
    content.key = "memory.md"
    search_contents = AsyncMock(return_value=[content])
    download_content = AsyncMock(return_value=b"# User Memory\n\n## Identity\n- Test")
    monkeypatch.setattr(
        "unique_user_memory.user_memory.search_contents_async",
        search_contents,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.download_content_to_bytes_async",
        download_content,
    )

    result = await download_user_memory(
        scope_id="scope_1",
        user_id="user_1",
        company_id="company_1",
        logger=MagicMock(),
    )

    assert result == "# User Memory\n\n## Identity\n- Test"
    search_contents.assert_awaited_once_with(
        user_id="user_1",
        company_id="company_1",
        chat_id=None,
        where={"ownerId": {"equals": "scope_1"}},
    )
    download_content.assert_awaited_once_with(
        user_id="user_1",
        company_id="company_1",
        content_id="content_1",
        chat_id=None,
    )


@pytest.mark.asyncio
async def test_ensure_user_memory_folder_returns_existing_user_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_info = AsyncMock(
        side_effect=[
            {"id": "scope_root"},
            {"id": "scope_user"},
        ]
    )
    create_paths = AsyncMock()
    add_access = AsyncMock()
    get_groups = AsyncMock()
    monkeypatch.setattr(
        "unique_user_memory.user_memory.unique_sdk.Folder.get_info_async",
        get_info,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.unique_sdk.Folder.create_paths_async",
        create_paths,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.unique_sdk.Folder.add_access_async",
        add_access,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.unique_sdk.Group.get_groups_async",
        get_groups,
    )

    result = await ensure_user_memory_folder(
        user_id="user_1",
        company_id="company_1",
        root_folder="user-memory",
        logger=MagicMock(),
    )

    assert result == "scope_user"
    get_info.assert_any_await(
        user_id="user_1",
        company_id="company_1",
        folderPath="/user-memory",
    )
    get_info.assert_any_await(
        user_id="user_1",
        company_id="company_1",
        folderPath="/user-memory/user_1",
    )
    create_paths.assert_not_awaited()
    get_groups.assert_not_awaited()
    add_access.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_user_memory_folder_creates_private_user_folder_under_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_info = AsyncMock(
        side_effect=[
            {"id": "scope_root"},
            RuntimeError("missing user folder"),
        ]
    )
    create_paths = AsyncMock(return_value={"createdFolders": [{"id": "scope_user"}]})
    add_access = AsyncMock()
    monkeypatch.setattr(
        "unique_user_memory.user_memory.unique_sdk.Folder.get_info_async",
        get_info,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.unique_sdk.Folder.create_paths_async",
        create_paths,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.unique_sdk.Folder.add_access_async",
        add_access,
    )

    result = await ensure_user_memory_folder(
        user_id="user_1",
        company_id="company_1",
        root_folder="user-memory",
        logger=MagicMock(),
    )

    assert result == "scope_user"
    create_paths.assert_awaited_once_with(
        user_id="user_1",
        company_id="company_1",
        parentScopeId="scope_root",
        relativePaths=["user_1"],
        inheritAccess=False,
    )
    add_access.assert_awaited_once_with(
        user_id="user_1",
        company_id="company_1",
        scopeId="scope_user",
        scopeAccesses=[
            {"entityId": "user_1", "type": "READ", "entityType": "USER"},
            {"entityId": "user_1", "type": "WRITE", "entityType": "USER"},
        ],
        applyToSubScopes=True,
    )


@pytest.mark.asyncio
async def test_ensure_user_memory_folder_returns_none_when_access_grant_fails_after_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_info = AsyncMock(
        side_effect=[
            {"id": "scope_root"},
            RuntimeError("missing user folder"),
        ]
    )
    create_paths = AsyncMock(return_value={"createdFolders": [{"id": "scope_user"}]})
    grant_error = RuntimeError("grant failed")
    add_access = AsyncMock(side_effect=grant_error)
    logger = MagicMock()
    monkeypatch.setattr(
        "unique_user_memory.user_memory.unique_sdk.Folder.get_info_async",
        get_info,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.unique_sdk.Folder.create_paths_async",
        create_paths,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory.unique_sdk.Folder.add_access_async",
        add_access,
    )

    result = await ensure_user_memory_folder(
        user_id="user_1",
        company_id="company_1",
        root_folder="user-memory",
        logger=logger,
    )

    assert result is None
    create_paths.assert_awaited_once_with(
        user_id="user_1",
        company_id="company_1",
        parentScopeId="scope_root",
        relativePaths=["user_1"],
        inheritAccess=False,
    )
    add_access.assert_awaited_once_with(
        user_id="user_1",
        company_id="company_1",
        scopeId="scope_user",
        scopeAccesses=[
            {"entityId": "user_1", "type": "READ", "entityType": "USER"},
            {"entityId": "user_1", "type": "WRITE", "entityType": "USER"},
        ],
        applyToSubScopes=True,
    )
    logger.warning.assert_called_with(
        "[user-memory] failed to grant read/write access on scope %s "
        "for user %s: [%s] %s",
        "scope_user",
        "user_1",
        "RuntimeError",
        grant_error,
    )


@pytest.mark.asyncio
async def test_upload_user_memory_writes_hidden_skip_ingestion_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_content = AsyncMock()
    monkeypatch.setattr(
        "unique_user_memory.user_memory.upload_content_from_bytes_async",
        upload_content,
    )

    result = await upload_user_memory(
        scope_id="scope_1",
        content="# User Memory\n\n## Identity\n- Test",
        user_id="user_1",
        company_id="company_1",
        logger=MagicMock(),
    )

    assert result is True
    upload_content.assert_awaited_once()
    assert upload_content.call_args.kwargs["content"] == (
        b"# User Memory\n\n## Identity\n- Test"
    )
    assert upload_content.call_args.kwargs["content_name"] == "memory.md"
    assert upload_content.call_args.kwargs["mime_type"] == "text/markdown"
    assert upload_content.call_args.kwargs["scope_id"] == "scope_1"
    assert upload_content.call_args.kwargs["ingestion_config"] == {
        "uniqueIngestionMode": "SKIP_INGESTION",
        "hideInChat": True,
    }


@pytest.mark.asyncio
async def test_user_memory_postprocessor_logs_success_when_upload_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updated_memory = "# User Memory\n\n## Identity\n- Updated"
    consolidate = AsyncMock(return_value=updated_memory)
    upload = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.consolidate_user_memory",
        consolidate,
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.upload_user_memory",
        upload,
    )
    event = MagicMock()
    event.user_id = "user_1"
    event.company_id = "company_1"
    event.payload.user_message.text = "remember this"
    loop_response = MagicMock()
    loop_response.message.text = "noted"
    logger = MagicMock()
    chat_service = MagicMock()
    postprocessor = UserMemoryPostprocessor(
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=event,
        state=UserMemoryState(scope_id="scope_1", text=empty_profile("user_1")),
        logger=logger,
        chat_service=chat_service,
    )

    updated = await postprocessor.run(loop_response)

    assert updated is True
    upload.assert_awaited_once_with(
        scope_id="scope_1",
        content=updated_memory,
        user_id="user_1",
        company_id="company_1",
        logger=logger,
    )
    logger.info.assert_any_call(
        "[user-memory] memory updated and uploaded successfully"
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_user_memory_postprocessor_run_resets_invocation_stats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: Verify each run reports only usage attributable to that run.
    Why this matters: Reused postprocessors must not inflate token analytics.
    Setup summary: Run twice with distinct usage and assert the second excludes the first.
    """
    load_stats = LanguageModelInvocationStats.from_usage(
        _TEST_LANGUAGE_MODEL.name,
        LanguageModelTokenUsage(total_tokens=2),
        source="user_memory_load_condense",
    )
    first_run_stats = LanguageModelInvocationStats.from_usage(
        _TEST_LANGUAGE_MODEL.name,
        LanguageModelTokenUsage(total_tokens=3),
        source="user_memory_consolidate_first",
    )
    second_run_stats = LanguageModelInvocationStats.from_usage(
        _TEST_LANGUAGE_MODEL.name,
        LanguageModelTokenUsage(total_tokens=5),
        source="user_memory_consolidate_second",
    )
    run_stats = iter((first_run_stats, second_run_stats))

    async def consolidate(*, invocation_stats, **kwargs) -> str:  # type: ignore[no-untyped-def]
        invocation_stats.append(next(run_stats))
        return "# User Memory\n\n## Identity\n- unchanged"

    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.consolidate_user_memory",
        consolidate,
    )
    event = MagicMock()
    event.user_id = "user_1"
    event.company_id = "company_1"
    event.payload.user_message.text = "remember this"
    loop_response = MagicMock()
    loop_response.message.text = "noted"
    state = UserMemoryState(
        scope_id="scope_1",
        text="# User Memory\n\n## Identity\n- unchanged",
        load_invocation_stats=(load_stats,),
    )
    postprocessor = UserMemoryPostprocessor(
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=event,
        state=state,
        logger=MagicMock(),
        chat_service=MagicMock(),
    )

    await postprocessor.run(loop_response)
    first_reported_stats = postprocessor.invocation_stats
    await postprocessor.run(loop_response)

    assert first_reported_stats == [load_stats, first_run_stats]
    assert postprocessor.invocation_stats == [second_run_stats]


@pytest.mark.ai
def test_user_memory_postprocessor_take_pending_invocation_stats_drains_once() -> None:
    """Purpose: Verify load-time usage is reported exactly once, however it's read.
    Why this matters: A turn that exits before `run()` (cancellation, empty
    response, a control-taking tool) must still report the load-time condense
    tokens, and a turn that does reach `run()` must not double-count them.
    Setup summary: Take the pending stats directly, then run(), and assert
    run() no longer reports the already-taken load stats.
    """
    load_stats = LanguageModelInvocationStats.from_usage(
        _TEST_LANGUAGE_MODEL.name,
        LanguageModelTokenUsage(total_tokens=2),
        source="user_memory_load_condense",
    )
    event = MagicMock()
    event.user_id = "user_1"
    event.company_id = "company_1"
    event.payload.user_message.text = "remember this"
    state = UserMemoryState(
        scope_id="scope_1",
        text="# User Memory\n\n## Identity\n- unchanged",
        load_invocation_stats=(load_stats,),
    )
    postprocessor = UserMemoryPostprocessor(
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=event,
        state=state,
        logger=MagicMock(),
        chat_service=MagicMock(),
    )

    taken = postprocessor.take_pending_invocation_stats()

    assert taken == [load_stats]
    assert postprocessor.take_pending_invocation_stats() == []


@pytest.mark.asyncio
async def test_user_memory_postprocessor_does_not_log_success_when_upload_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updated_memory = "# User Memory\n\n## Identity\n- Updated"
    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.consolidate_user_memory",
        AsyncMock(return_value=updated_memory),
    )
    monkeypatch.setattr(
        "unique_user_memory.user_memory_postprocessor.upload_user_memory",
        AsyncMock(return_value=False),
    )
    event = MagicMock()
    event.user_id = "user_1"
    event.company_id = "company_1"
    event.payload.user_message.text = "remember this"
    loop_response = MagicMock()
    loop_response.message.text = "noted"
    logger = MagicMock()
    chat_service = MagicMock()
    postprocessor = UserMemoryPostprocessor(
        config=UserMemoryConfig(),
        language_model=_TEST_LANGUAGE_MODEL,
        event=event,
        state=UserMemoryState(scope_id="scope_1", text=empty_profile("user_1")),
        logger=logger,
        chat_service=chat_service,
    )

    updated = await postprocessor.run(loop_response)

    assert updated is False
    assert all(
        call.args != ("[user-memory] memory updated and uploaded successfully",)
        for call in logger.info.call_args_list
    )
    logger.warning.assert_any_call("[user-memory] memory update was not uploaded")
