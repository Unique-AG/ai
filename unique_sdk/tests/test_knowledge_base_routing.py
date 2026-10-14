"""Tests for routing Knowledge Base writes through ``/sandbox-knowledge-base``."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import unique_sdk
from unique_sdk._error import PermissionError as SdkPermissionError
from unique_sdk._knowledge_base_routing import (
    SANDBOX_KB_WRITES_ENV_VAR,
    knowledge_base_write_url,
    sandbox_kb_writes_from_env,
)
from unique_sdk.api_resources._content import Content
from unique_sdk.api_resources._folder import Folder
from unique_sdk.utils import file_io

pytestmark = [pytest.mark.ai, pytest.mark.unit]

USER_ID = "user_1"
COMPANY_ID = "company_1"
SCOPE_ID = "scope_1"
CONTENT_ID = "cont_1"
VERSION_ID = "cver_1"
PREFIX = "/sandbox-knowledge-base"


@pytest.fixture
def sandbox_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(unique_sdk, "sandbox_knowledge_base_writes", True)


@pytest.fixture
def generic_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(unique_sdk, "sandbox_knowledge_base_writes", False)


class TestEnvParsing:
    @pytest.mark.parametrize(
        "value", ["1", "true", "TRUE", "True", "yes", "YES", " yes ", "\ttrue\n"]
    )
    def test_truthy_values_enable(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv(SANDBOX_KB_WRITES_ENV_VAR, value)
        assert sandbox_kb_writes_from_env() is True

    @pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "on", "y", "2"])
    def test_other_values_disable(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv(SANDBOX_KB_WRITES_ENV_VAR, value)
        assert sandbox_kb_writes_from_env() is False

    def test_unset_disables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(SANDBOX_KB_WRITES_ENV_VAR, raising=False)
        assert sandbox_kb_writes_from_env() is False

    def test_env_var_name(self) -> None:
        assert SANDBOX_KB_WRITES_ENV_VAR == "UNIQUE_SDK_SANDBOX_KB_WRITES"

    @pytest.mark.parametrize(("value", "expected"), [("true", True), (None, False)])
    def test_module_setting_initialised_from_env_on_import(
        self, value: str | None, expected: bool
    ) -> None:
        env = {k: v for k, v in os.environ.items() if k != SANDBOX_KB_WRITES_ENV_VAR}
        if value is not None:
            env[SANDBOX_KB_WRITES_ENV_VAR] = value
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import unique_sdk; print(unique_sdk.sandbox_knowledge_base_writes)",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == str(expected)


class TestKnowledgeBaseWriteUrl:
    def test_prefixes_when_enabled(self, sandbox_writes: None) -> None:
        assert knowledge_base_write_url("/folder") == f"{PREFIX}/folder"

    def test_unchanged_when_disabled(self, generic_writes: None) -> None:
        assert knowledge_base_write_url("/folder") == "/folder"


# (name, resource, sync method, async method, kwargs, http method, generic path)
WRITE_METHODS: list[tuple[str, type, str, str, dict[str, Any], str, str]] = [
    (
        "folder_create_paths",
        Folder,
        "create_paths",
        "create_paths_async",
        {"paths": ["/A/B"]},
        "post",
        "/folder",
    ),
    (
        "folder_update",
        Folder,
        "update",
        "update_async",
        {"scopeId": SCOPE_ID, "name": "New"},
        "patch",
        f"/folder/{SCOPE_ID}",
    ),
    (
        "folder_delete",
        Folder,
        "delete",
        "delete_async",
        {"scopeId": SCOPE_ID},
        "delete",
        f"/folder/{SCOPE_ID}",
    ),
    (
        "content_upsert",
        Content,
        "upsert",
        "upsert_async",
        {"scopeId": SCOPE_ID, "input": {"key": "a.txt", "mimeType": "text/plain"}},
        "post",
        "/content/upsert",
    ),
    (
        "content_update",
        Content,
        "update",
        "update_async",
        {"contentId": CONTENT_ID, "title": "b.txt"},
        "patch",
        f"/content/{CONTENT_ID}",
    ),
    (
        "content_delete",
        Content,
        "delete",
        "delete_async",
        {"contentId": CONTENT_ID},
        "delete",
        f"/content/{CONTENT_ID}",
    ),
    (
        "content_restore_version",
        Content,
        "restore_version",
        "restore_version_async",
        {"contentVersionId": VERSION_ID},
        "post",
        f"/content/versions/{VERSION_ID}/restore",
    ),
]

_WRITE_IDS = [m[0] for m in WRITE_METHODS]


def _called_path(mock: MagicMock) -> tuple[str, str]:
    mock.assert_called_once()
    method, path = mock.call_args.args[:2]
    return method, path


@pytest.mark.parametrize(
    ("name", "resource", "sync_name", "async_name", "kwargs", "http", "path"),
    WRITE_METHODS,
    ids=_WRITE_IDS,
)
class TestWriteMethodRouting:
    @pytest.mark.parametrize(
        ("enabled", "expected_prefix"), [(True, PREFIX), (False, "")]
    )
    def test_sync(
        self,
        monkeypatch: pytest.MonkeyPatch,
        name: str,
        resource: type,
        sync_name: str,
        async_name: str,
        kwargs: dict[str, Any],
        http: str,
        path: str,
        enabled: bool,
        expected_prefix: str,
    ) -> None:
        monkeypatch.setattr(unique_sdk, "sandbox_knowledge_base_writes", enabled)
        with patch.object(resource, "_static_request", return_value={}) as mock:
            getattr(resource, sync_name)(
                user_id=USER_ID, company_id=COMPANY_ID, **dict(kwargs)
            )
        assert _called_path(mock) == (http, f"{expected_prefix}{path}")

    @pytest.mark.parametrize(
        ("enabled", "expected_prefix"), [(True, PREFIX), (False, "")]
    )
    async def test_async(
        self,
        monkeypatch: pytest.MonkeyPatch,
        name: str,
        resource: type,
        sync_name: str,
        async_name: str,
        kwargs: dict[str, Any],
        http: str,
        path: str,
        enabled: bool,
        expected_prefix: str,
    ) -> None:
        monkeypatch.setattr(unique_sdk, "sandbox_knowledge_base_writes", enabled)
        with patch.object(
            resource, "_static_request_async", new_callable=AsyncMock, return_value={}
        ) as mock:
            await getattr(resource, async_name)(
                user_id=USER_ID, company_id=COMPANY_ID, **dict(kwargs)
            )
        assert _called_path(mock) == (http, f"{expected_prefix}{path}")


# (resource, sync method, async method, kwargs, http method, path)
UNAFFECTED_METHODS: list[tuple[type, str, str, dict[str, Any], str, str]] = [
    (
        Folder,
        "get_info",
        "get_info_async",
        {"scopeId": SCOPE_ID},
        "get",
        "/folder/info",
    ),
    (Folder, "get_infos", "get_infos_async", {}, "get", "/folder/infos"),
    (
        Folder,
        "get_folder_path",
        "get_folder_path_async",
        {"scope_id": SCOPE_ID},
        "get",
        f"/folder/{SCOPE_ID}/path",
    ),
    (
        Folder,
        "update_ingestion_config",
        "update_ingestion_config_async",
        {"scopeId": SCOPE_ID, "ingestionConfig": {}, "applyToSubScopes": False},
        "patch",
        "/folder/ingestion-config",
    ),
    (
        Folder,
        "add_access",
        "add_access_async",
        {"scopeId": SCOPE_ID, "scopeAccesses": [], "applyToSubScopes": False},
        "patch",
        "/folder/add-access",
    ),
    (
        Folder,
        "remove_access",
        "remove_access_async",
        {"scopeId": SCOPE_ID, "scopeAccesses": [], "applyToSubScopes": False},
        "patch",
        "/folder/remove-access",
    ),
    (
        Folder,
        "move",
        "move_async",
        {"folderId": SCOPE_ID, "parentId": "scope_2"},
        "post",
        f"/folder/{SCOPE_ID}/move",
    ),
    (Content, "search", "search_async", {"where": {}}, "post", "/content/search"),
    (Content, "get_info", "get_info_async", {}, "post", "/content/info"),
    (Content, "get_infos", "get_infos_async", {}, "post", "/content/infos"),
    (
        Content,
        "versions",
        "versions_async",
        {"contentId": CONTENT_ID},
        "get",
        f"/content/{CONTENT_ID}/versions",
    ),
    (
        Content,
        "version_download_url",
        "version_download_url_async",
        {"contentVersionId": VERSION_ID},
        "get",
        f"/content/versions/{VERSION_ID}/download-url",
    ),
    (
        Content,
        "ingest_magic_table_sheets",
        "ingest_magic_table_sheets_async",
        {"data": [], "ingestionConfiguration": {}, "metadata": {}, "scopeId": SCOPE_ID},
        "post",
        "/content/magic-table-sheets",
    ),
    (
        Content,
        "update_ingestion_state",
        "update_ingestion_state_async",
        {"contentId": CONTENT_ID, "ingestionState": "QUEUED"},
        "patch",
        f"/content/{CONTENT_ID}/ingestion-state",
    ),
]

_UNAFFECTED_IDS = [f"{m[0].__name__}.{m[1]}" for m in UNAFFECTED_METHODS]


@pytest.mark.parametrize(
    ("resource", "sync_name", "async_name", "kwargs", "http", "path"),
    UNAFFECTED_METHODS,
    ids=_UNAFFECTED_IDS,
)
class TestOtherMethodsUnaffected:
    def test_sync(
        self,
        sandbox_writes: None,
        resource: type,
        sync_name: str,
        async_name: str,
        kwargs: dict[str, Any],
        http: str,
        path: str,
    ) -> None:
        with patch.object(resource, "_static_request", return_value={}) as mock:
            getattr(resource, sync_name)(USER_ID, COMPANY_ID, **dict(kwargs))
        assert _called_path(mock) == (http, path)

    async def test_async(
        self,
        sandbox_writes: None,
        resource: type,
        sync_name: str,
        async_name: str,
        kwargs: dict[str, Any],
        http: str,
        path: str,
    ) -> None:
        with patch.object(
            resource, "_static_request_async", new_callable=AsyncMock, return_value={}
        ) as mock:
            await getattr(resource, async_name)(USER_ID, COMPANY_ID, **dict(kwargs))
        assert _called_path(mock) == (http, path)


class TestFolderPathAutoCreate:
    def test_upsert_creates_missing_parent_via_sandbox_route(
        self, sandbox_writes: None
    ) -> None:
        def fake_request(method: str, url: str, *args: Any, **kwargs: Any) -> Any:
            if url == "/folder/info":
                raise unique_sdk.InvalidRequestError("not found", None)
            if url == f"{PREFIX}/folder":
                return {"createdFolders": [{"id": SCOPE_ID}]}
            return {}

        with (
            patch.object(Folder, "_static_request", side_effect=fake_request) as fmock,
            patch.object(Content, "_static_request", return_value={}) as cmock,
        ):
            Content.upsert(
                user_id=USER_ID,
                company_id=COMPANY_ID,
                parentFolderPath="/New/Folder",
                input={"key": "a.txt", "mimeType": "text/plain"},
            )

        assert [c.args[:2] for c in fmock.call_args_list] == [
            ("get", "/folder/info"),
            ("post", f"{PREFIX}/folder"),
        ]
        assert _called_path(cmock) == ("post", f"{PREFIX}/content/upsert")
        assert cmock.call_args.kwargs["params"]["scopeId"] == SCOPE_ID


class TestUploadFile:
    @pytest.mark.parametrize(
        ("enabled", "expected_prefix"), [(True, PREFIX), (False, "")]
    )
    def test_upload_file_upserts_via_routed_path_and_puts_to_write_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
        enabled: bool,
        expected_prefix: str,
    ) -> None:
        monkeypatch.setattr(unique_sdk, "sandbox_knowledge_base_writes", enabled)
        monkeypatch.setattr(unique_sdk, "ingestion_upload_api_url_internal", None)
        local = tmp_path / "a.txt"
        local.write_bytes(b"hello")
        write_url = "https://blob.example/write?sig=1"
        created = MagicMock(
            id=CONTENT_ID, writeUrl=write_url, readUrl="https://blob.example/read"
        )
        put_response = MagicMock(status_code=201)

        with (
            patch.object(Content, "_static_request", return_value=created) as mock,
            patch.object(file_io.requests, "put", return_value=put_response) as put,
        ):
            file_io.upload_file(
                userId=USER_ID,
                companyId=COMPANY_ID,
                path_to_file=str(local),
                displayed_filename="a.txt",
                mime_type="text/plain",
                scope_or_unique_path=SCOPE_ID,
            )

        assert [c.args[:2] for c in mock.call_args_list] == [
            ("post", f"{expected_prefix}/content/upsert"),
            ("post", f"{expected_prefix}/content/upsert"),
        ]
        put.assert_called_once()
        assert put.call_args.args[0] == write_url


def _fake_http_client(body: str, status: int) -> MagicMock:
    client = MagicMock()
    client.name = "fake"
    client.request.return_value = (body, status, {})
    return client


class TestHttpLayer:
    @pytest.fixture(autouse=True)
    def _credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(unique_sdk, "api_key", "ukey_test")
        monkeypatch.setattr(unique_sdk, "app_id", "app_test")

    def test_sandbox_path_reaches_http_client_under_api_base(
        self, monkeypatch: pytest.MonkeyPatch, sandbox_writes: None
    ) -> None:
        client = _fake_http_client('{"id": "cont_1"}', 200)
        monkeypatch.setattr(unique_sdk, "default_http_client", client)
        monkeypatch.setattr(unique_sdk, "api_base", "https://gw.example/public/chat")

        Content.delete(user_id=USER_ID, company_id=COMPANY_ID, contentId=CONTENT_ID)

        method, url = client.request.call_args.args[:2]
        assert method == "delete"
        assert url == f"https://gw.example/public/chat{PREFIX}/content/{CONTENT_ID}"

    def test_403_raises_permission_error_with_server_message(
        self, monkeypatch: pytest.MonkeyPatch, sandbox_writes: None
    ) -> None:
        message = "Skills cannot be changed from a Conduct sandbox."
        body = (
            '{"error": {"type": "api_error", "code": null, '
            f'"message": "{message}", "params": null}}}}'
        )
        monkeypatch.setattr(
            unique_sdk, "default_http_client", _fake_http_client(body, 403)
        )

        with pytest.raises(SdkPermissionError) as excinfo:
            Content.delete(user_id=USER_ID, company_id=COMPANY_ID, contentId=CONTENT_ID)

        assert excinfo.value.http_status == 403
        assert str(excinfo.value).startswith(message)
