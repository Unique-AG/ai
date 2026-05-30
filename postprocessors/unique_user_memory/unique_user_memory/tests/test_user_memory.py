from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_user_memory.config import UserMemoryConfig
from unique_user_memory.user_memory import (
    _sanitize_for_xml_context,
    consolidate_user_memory,
    download_user_memory,
    enforce_token_cap,
    upload_user_memory,
)
from unique_user_memory.user_memory_prompts import empty_profile


def test_enforce_token_cap_truncates_long_content() -> None:
    content = "\n\n".join(f"paragraph {index} " + "word " * 40 for index in range(50))

    capped = enforce_token_cap(content, max_tokens=120)

    assert "<!-- truncated to fit memory budget -->" in capped
    assert len(capped) < len(content)


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

    result = await consolidate_user_memory(
        current_memory=current,
        user_id="user_1",
        user_message="hello",
        assistant_message="hi",
        config=UserMemoryConfig(enabled=True),
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

    result = await consolidate_user_memory(
        current_memory=current,
        user_id="user_1",
        user_message="remember I like concise answers",
        assistant_message="noted",
        config=UserMemoryConfig(enabled=True),
        event=MagicMock(),
        logger=MagicMock(),
    )

    assert result == current


@pytest.mark.asyncio
async def test_download_user_memory_returns_empty_when_file_missing() -> None:
    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[])

    result = await download_user_memory(
        scope_id="scope_1",
        chat_id="chat_1",
        content_service=content_service,
        logger=MagicMock(),
    )

    assert result == ""


@pytest.mark.asyncio
async def test_upload_user_memory_writes_hidden_skip_ingestion_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_file = MagicMock()
    monkeypatch.setattr("unique_user_memory.user_memory.file_io.upload_file", upload_file)

    result = await upload_user_memory(
        scope_id="scope_1",
        content="# User Memory\n\n## Identity\n- Test",
        user_id="user_1",
        company_id="company_1",
        logger=MagicMock(),
    )

    assert result is True
    upload_file.assert_called_once()
    _, _, uploaded_path, filename, mime_type = upload_file.call_args.args[:5]
    assert Path(uploaded_path).exists() is False
    assert filename == "memory.md"
    assert mime_type == "text/markdown"
    assert upload_file.call_args.kwargs["scope_or_unique_path"] == "scope_1"
    assert upload_file.call_args.kwargs["ingestion_config"] == {
        "uniqueIngestionMode": "SKIP_INGESTION",
        "hideInChat": True,
    }
