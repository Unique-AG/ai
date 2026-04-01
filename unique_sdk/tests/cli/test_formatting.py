"""Tests for unique_sdk.cli.formatting."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from unique_sdk.cli.formatting import (
    format_content_info,
    format_folder_info,
    format_ls,
    format_mcp_response,
    format_search_results,
)


def _folder(
    name: str = "Reports",
    fid: str = "scope_abc",
    updated: str | None = "2025-03-01T10:00:00Z",
    parent: str | None = "scope_root",
) -> dict[str, Any]:
    return {
        "id": fid,
        "name": name,
        "ingestionConfig": {},
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": updated,
        "parentId": parent,
    }


def _file(
    title: str = "report.pdf",
    cid: str = "cont_123",
    size: int = 1024,
    updated: str | None = "2025-03-10T09:00:00Z",
) -> dict[str, Any]:
    return {
        "id": cid,
        "key": "report.pdf",
        "url": None,
        "title": title,
        "metadata": None,
        "mimeType": "application/pdf",
        "description": None,
        "byteSize": size,
        "ownerId": "user_1",
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": updated,
    }


class TestFormatLs:
    def test_empty(self) -> None:
        assert format_ls([], []) == "(empty)"

    def test_folders_only(self) -> None:
        result = format_ls([_folder()], [])
        assert "DIR" in result
        assert "Reports/" in result
        assert "scope_abc" in result

    def test_files_only(self) -> None:
        result = format_ls([], [_file()])
        assert "FILE" in result
        assert "report.pdf" in result
        assert "cont_123" in result

    def test_mixed(self) -> None:
        result = format_ls([_folder()], [_file()])
        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert "DIR" in lines[0]
        assert "FILE" in lines[1]

    def test_size_formatting(self) -> None:
        result = format_ls([], [_file(size=0)])
        assert "0 B" in result

        result = format_ls([], [_file(size=5_000_000)])
        assert "4.8 MB" in result

        result = format_ls([], [_file(size=2_000_000_000)])
        assert "1.9 GB" in result

    def test_date_formatting(self) -> None:
        result = format_ls([_folder(updated="2025-03-01T10:30:00Z")], [])
        assert "2025-03-01 10:30" in result

    def test_missing_date(self) -> None:
        result = format_ls([_folder(updated=None)], [])
        assert "-" in result

    def test_file_without_title_uses_key(self) -> None:
        f = _file()
        f["title"] = None
        result = format_ls([], [f])
        assert "report.pdf" in result


class TestFormatSearchResults:
    def test_no_results(self) -> None:
        assert format_search_results([]) == "No results found."

    def test_single_result(self) -> None:
        r = MagicMock()
        r.title = "doc.pdf"
        r.id = "cont_1"
        r.startPage = 5
        r.endPage = 6
        r.text = "some relevant text here"
        result = format_search_results([r])
        assert "Found 1 result(s)" in result
        assert "doc.pdf" in result
        assert "(p.5-6)" in result
        assert "cont_1" in result
        assert "some relevant text here" in result

    def test_single_page(self) -> None:
        r = MagicMock()
        r.title = "doc.pdf"
        r.id = "cont_1"
        r.startPage = 3
        r.endPage = 3
        r.text = "text"
        result = format_search_results([r])
        assert "(p.3)" in result

    def test_no_pages(self) -> None:
        r = MagicMock()
        r.title = "doc.pdf"
        r.id = "cont_1"
        r.startPage = None
        r.endPage = None
        r.text = "text"
        result = format_search_results([r])
        assert "(p." not in result

    def test_long_snippet_truncated(self) -> None:
        r = MagicMock()
        r.title = "doc.pdf"
        r.id = "cont_1"
        r.startPage = None
        r.endPage = None
        r.text = "x" * 200
        result = format_search_results([r])
        assert "..." in result

    def test_empty_text(self) -> None:
        r = MagicMock()
        r.title = "doc.pdf"
        r.id = "cont_1"
        r.startPage = None
        r.endPage = None
        r.text = ""
        result = format_search_results([r])
        assert "doc.pdf" in result


class TestFormatContentInfo:
    def test_basic(self) -> None:
        result = format_content_info(_file())
        assert "cont_123" in result
        assert "report.pdf" in result
        assert "application/pdf" in result
        assert "1.0 KB" in result
        assert "user_1" in result


class TestFormatFolderInfo:
    def test_basic(self) -> None:
        result = format_folder_info(_folder())
        assert "scope_abc" in result
        assert "Reports" in result
        assert "scope_root" in result

    def test_root_parent(self) -> None:
        result = format_folder_info(_folder(parent=None))
        assert "(root)" in result


def _mcp_response(
    name: str = "search",
    is_error: bool = False,
    server_id: str = "mcp_srv_1",
    content: list[dict[str, Any]] | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.name = name
    resp.isError = is_error
    resp.mcpServerId = server_id
    resp.content = content if content is not None else []
    return resp


class TestFormatMcpResponse:
    def test_basic_text(self) -> None:
        resp = _mcp_response(content=[{"type": "text", "text": "hello world"}])
        result = format_mcp_response(resp)
        assert "MCP tool call: search" in result
        assert "Server: mcp_srv_1" in result
        assert "[text] hello world" in result

    def test_error_flag(self) -> None:
        resp = _mcp_response(is_error=True, content=[{"type": "text", "text": "fail"}])
        result = format_mcp_response(resp)
        assert "(ERROR)" in result

    def test_no_error_flag(self) -> None:
        resp = _mcp_response(content=[])
        result = format_mcp_response(resp)
        assert "(ERROR)" not in result

    def test_multiline_text(self) -> None:
        resp = _mcp_response(content=[{"type": "text", "text": "line1\nline2\nline3"}])
        result = format_mcp_response(resp)
        assert "[text] line1" in result
        assert "[text] line2" in result
        assert "[text] line3" in result

    def test_image_content(self) -> None:
        resp = _mcp_response(
            content=[{"type": "image", "mimeType": "image/png", "data": "base64data"}]
        )
        result = format_mcp_response(resp)
        assert "[image]" in result
        assert "image/png" in result

    def test_audio_content(self) -> None:
        resp = _mcp_response(
            content=[{"type": "audio", "mimeType": "audio/mp3", "data": "base64data"}]
        )
        result = format_mcp_response(resp)
        assert "[audio]" in result
        assert "audio/mp3" in result

    def test_resource_link(self) -> None:
        resp = _mcp_response(
            content=[
                {
                    "type": "resource_link",
                    "name": "doc",
                    "uri": "https://example.com",
                    "description": "A doc",
                }
            ]
        )
        result = format_mcp_response(resp)
        assert "[resource_link] doc: https://example.com" in result
        assert "A doc" in result

    def test_resource_link_no_description(self) -> None:
        resp = _mcp_response(
            content=[
                {"type": "resource_link", "name": "doc", "uri": "https://example.com"}
            ]
        )
        result = format_mcp_response(resp)
        assert "[resource_link] doc: https://example.com" in result

    def test_text_resource(self) -> None:
        resp = _mcp_response(
            content=[
                {
                    "type": "resource",
                    "resource": {
                        "uri": "file:///data.txt",
                        "text": "content here",
                    },
                }
            ]
        )
        result = format_mcp_response(resp)
        assert "[resource] file:///data.txt" in result
        assert "content here" in result

    def test_blob_resource(self) -> None:
        resp = _mcp_response(
            content=[
                {
                    "type": "resource",
                    "resource": {
                        "uri": "file:///img.png",
                        "mimeType": "image/png",
                        "blob": "base64data",
                    },
                }
            ]
        )
        result = format_mcp_response(resp)
        assert "[resource] file:///img.png" in result
        assert "image/png" in result

    def test_empty_resource(self) -> None:
        resp = _mcp_response(content=[{"type": "resource", "resource": None}])
        result = format_mcp_response(resp)
        assert "[resource] (empty)" in result

    def test_unsupported_type(self) -> None:
        resp = _mcp_response(content=[{"type": "video"}])
        result = format_mcp_response(resp)
        assert "[video] (unsupported content type)" in result

    def test_empty_content(self) -> None:
        resp = _mcp_response(content=[])
        result = format_mcp_response(resp)
        assert "MCP tool call: search" in result
        assert "Server: mcp_srv_1" in result

    def test_image_no_mime(self) -> None:
        resp = _mcp_response(content=[{"type": "image", "data": "base64data"}])
        result = format_mcp_response(resp)
        assert "image/*" in result

    def test_audio_no_mime(self) -> None:
        resp = _mcp_response(content=[{"type": "audio", "data": "base64data"}])
        result = format_mcp_response(resp)
        assert "audio/*" in result
