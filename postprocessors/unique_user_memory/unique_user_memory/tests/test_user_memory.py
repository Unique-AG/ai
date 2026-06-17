from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_user_memory.config import UserMemoryConfig
from unique_user_memory.user_memory import (
    UserMemoryState,
    _sanitize_for_xml_context,
    consolidate_user_memory,
    count_tokens,
    download_user_memory,
    enforce_token_cap,
    ensure_user_memory_folder,
    upload_user_memory,
)
from unique_user_memory.user_memory_postprocessor import UserMemoryPostprocessor
from unique_user_memory.user_memory_prompts import empty_profile


def test_enforce_token_cap_truncates_long_content() -> None:
    content = "\n\n".join(f"paragraph {index} " + "word " * 40 for index in range(50))

    capped = enforce_token_cap(content=content, max_tokens=120)

    assert "<!-- truncated to fit memory budget -->" in capped
    assert len(capped) < len(content)


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
    postprocessor = UserMemoryPostprocessor(
        config=UserMemoryConfig(enabled=True),
        event=event,
        state=UserMemoryState(scope_id="scope_1", text=empty_profile("user_1")),
        logger=logger,
    )

    await postprocessor.run(loop_response)

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
    postprocessor = UserMemoryPostprocessor(
        config=UserMemoryConfig(enabled=True),
        event=event,
        state=UserMemoryState(scope_id="scope_1", text=empty_profile("user_1")),
        logger=logger,
    )

    await postprocessor.run(loop_response)

    assert all(
        call.args != ("[user-memory] memory updated and uploaded successfully",)
        for call in logger.info.call_args_list
    )
    logger.warning.assert_any_call("[user-memory] memory update was not uploaded")
