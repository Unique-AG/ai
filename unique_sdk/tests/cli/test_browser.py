"""Tests for the unique-cli browser command (browser steering)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from unique_sdk.cli.cli import main as cli_main
from unique_sdk.cli.commands.browser import (
    BrowserConfigError,
    cmd_browser_action,
    cmd_browser_download,
    cmd_browser_status,
    is_error_output,
    load_browser_config,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState

_BRIDGE_URL = "https://gateway.qa.example/browser-bridge"


def _config() -> Config:
    return Config(
        user_id="u1",
        company_id="c1",
        api_key="key",
        app_id="app",
        api_base="https://example.com",
    )


def _state() -> ShellState:
    return ShellState(_config())


def _write_browser_config(path: Path, *, bridge_url: str = _BRIDGE_URL) -> None:
    path.write_text(
        json.dumps({"bridgeUrl": bridge_url, "installUrl": None}),
        encoding="utf-8",
    )


def _mock_response(
    *,
    ok: bool = True,
    status_code: int = 200,
    json_body: Any = None,
    text: str = "",
    headers: dict[str, str] | None = None,
    raise_on_json: bool = False,
) -> MagicMock:
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    resp.text = text
    resp.headers = headers or {}
    if raise_on_json:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_body
    return resp


# ── config loading ────────────────────────────────────────────────────────────


def test_load_browser_config_missing_raises(tmp_path: Path) -> None:
    try:
        load_browser_config(str(tmp_path / "nope.json"))
    except BrowserConfigError as exc:
        assert "not found" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected BrowserConfigError")


def test_load_browser_config_without_bridge_url_raises(tmp_path: Path) -> None:
    path = tmp_path / ".unique-browser.json"
    path.write_text(json.dumps({"installUrl": None}), encoding="utf-8")
    try:
        load_browser_config(str(path))
    except BrowserConfigError as exc:
        assert "bridgeUrl" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected BrowserConfigError")


# ── action verb ─────────────────────────────────────────────────────────────


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cmd_browser_action_posts_to_bridge(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    mock_post.return_value = _mock_response(
        json_body={"ok": True, "result": {"tree": "root"}}
    )

    output = cmd_browser_action(_state(), "get-dom", {}, config_path=str(config_path))

    parsed = json.loads(output)
    assert parsed == {"ok": True, "result": {"tree": "root"}}
    assert not is_error_output(output)

    url = mock_post.call_args.args[0]
    assert url == f"{_BRIDGE_URL}/public/browser/action"
    body = json.loads(mock_post.call_args.kwargs["data"])
    assert body == {"verb": "get-dom", "args": {}}
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["x-user-id"] == "u1"
    assert headers["x-company-id"] == "c1"
    assert headers["Authorization"] == "Bearer key"


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cmd_browser_action_forwards_tab_id_and_args(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    mock_post.return_value = _mock_response(json_body={"ok": True, "result": None})

    cmd_browser_action(
        _state(),
        "click",
        {"ref": "e42"},
        tab_id=7,
        config_path=str(config_path),
    )

    body = json.loads(mock_post.call_args.kwargs["data"])
    assert body == {"verb": "click", "args": {"ref": "e42"}, "tabId": 7}


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cmd_browser_action_passes_through_not_connected(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    mock_post.return_value = _mock_response(
        ok=False,
        status_code=424,
        json_body={
            "error": "browser_not_connected",
            "message": "No connected extension.",
            "userActionRequired": True,
            "installUrl": None,
            "remediation": "Ask the user to install the extension.",
        },
    )

    output = cmd_browser_action(_state(), "get-dom", {}, config_path=str(config_path))

    parsed = json.loads(output)
    assert parsed["ok"] is False
    assert parsed["error"] == "browser_not_connected"
    assert parsed["remediation"].startswith("Ask the user")
    assert is_error_output(output)


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cmd_browser_action_bridge_unreachable(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    import requests

    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    mock_post.side_effect = requests.ConnectionError("refused")

    output = cmd_browser_action(_state(), "get-dom", {}, config_path=str(config_path))
    parsed = json.loads(output)
    assert parsed["ok"] is False
    assert parsed["error"] == "browser_bridge_unreachable"
    assert is_error_output(output)


def test_cmd_browser_action_not_configured(tmp_path: Path) -> None:
    output = cmd_browser_action(
        _state(), "get-dom", {}, config_path=str(tmp_path / "absent.json")
    )
    parsed = json.loads(output)
    assert parsed["ok"] is False
    assert parsed["error"] == "browser_not_configured"


# ── status ──────────────────────────────────────────────────────────────────


@patch("unique_sdk.cli.commands.browser.requests.get")
def test_cmd_browser_status(mock_get: MagicMock, tmp_path: Path) -> None:
    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    mock_get.return_value = _mock_response(
        json_body={"connected": True, "installUrl": None}
    )

    output = cmd_browser_status(_state(), config_path=str(config_path))
    parsed = json.loads(output)
    assert parsed == {"ok": True, "result": {"connected": True, "installUrl": None}}
    # A successful status body has no `ok: false`, so it is not an error.
    assert not is_error_output(output)
    assert mock_get.call_args.args[0] == f"{_BRIDGE_URL}/public/browser/status"


# ── download ──────────────────────────────────────────────────────────────────


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cmd_browser_download_streams_to_dest(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    resp = _mock_response(
        headers={
            "Content-Type": "application/pdf",
            "X-Browser-File-Name": "report.pdf",
            "X-Browser-Total-Bytes": "8",
        }
    )
    resp.iter_content.return_value = [b"1234", b"5678"]
    mock_post.return_value = resp

    dest = tmp_path / "output" / "report.pdf"
    output = cmd_browser_download(
        _state(),
        "https://portal/report.pdf",
        str(dest),
        config_path=str(config_path),
    )

    parsed = json.loads(output)
    assert parsed["ok"] is True
    assert parsed["result"]["bytes"] == 8
    assert parsed["result"]["fileName"] == "report.pdf"
    assert dest.read_bytes() == b"12345678"
    assert mock_post.call_args.args[0] == f"{_BRIDGE_URL}/public/browser/download"
    assert mock_post.call_args.kwargs["stream"] is True


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cmd_browser_download_error_before_stream(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    mock_post.return_value = _mock_response(
        ok=False,
        status_code=413,
        json_body={"error": "browser_download_too_large", "message": "too big"},
    )

    dest = tmp_path / "out.pdf"
    output = cmd_browser_download(
        _state(), "https://portal/big.pdf", str(dest), config_path=str(config_path)
    )
    parsed = json.loads(output)
    assert parsed["ok"] is False
    assert parsed["error"] == "browser_download_too_large"
    assert not dest.exists()


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cmd_browser_download_stream_error_removes_partial_file(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    import requests

    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    resp = _mock_response(headers={"X-Browser-File-Name": "report.pdf"})

    def _dropping_stream():
        yield b"partial"
        raise requests.ConnectionError("dropped")

    resp.iter_content.return_value = _dropping_stream()
    mock_post.return_value = resp

    dest = tmp_path / "out" / "report.pdf"
    output = cmd_browser_download(
        _state(), "https://portal/report.pdf", str(dest), config_path=str(config_path)
    )

    parsed = json.loads(output)
    assert parsed["ok"] is False
    assert parsed["error"] == "browser_bridge_unreachable"
    # The truncated bytes must not survive a failed stream.
    assert not dest.exists()


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cmd_browser_download_write_error_removes_partial_file(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    resp = _mock_response(headers={"X-Browser-File-Name": "report.pdf"})
    resp.iter_content.return_value = [b"1234", b"5678"]
    mock_post.return_value = resp

    dest = tmp_path / "out" / "report.pdf"
    dest.parent.mkdir(parents=True)
    # Force an OSError on the second write by revoking the writable handle.
    real_open = Path.open

    def _flaky_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        handle = real_open(self, *args, **kwargs)
        original_write = handle.write

        def _write(data: bytes) -> int:
            if handle.tell() > 0:
                raise OSError("disk full")
            return original_write(data)

        handle.write = _write  # type: ignore[method-assign]
        return handle

    with patch.object(Path, "open", _flaky_open):
        output = cmd_browser_download(
            _state(),
            "https://portal/report.pdf",
            str(dest),
            config_path=str(config_path),
        )

    parsed = json.loads(output)
    assert parsed["ok"] is False
    assert parsed["error"] == "browser_download_write_failed"
    assert not dest.exists()


# ── Click wiring ──────────────────────────────────────────────────────────────


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cli_browser_click_requires_target(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)

    runner = CliRunner()
    with patch.dict(
        "os.environ",
        {
            "UNIQUE_USER_ID": "u1",
            "UNIQUE_COMPANY_ID": "c1",
            "UNIQUE_BROWSER_CONFIG": str(config_path),
        },
    ):
        result = runner.invoke(cli_main, ["browser", "click"])

    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] == "browser_missing_target"
    mock_post.assert_not_called()


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cli_browser_navigate_exit_zero_on_success(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    mock_post.return_value = _mock_response(
        json_body={"ok": True, "result": {"url": "https://example.com"}}
    )

    runner = CliRunner()
    with patch.dict(
        "os.environ",
        {
            "UNIQUE_USER_ID": "u1",
            "UNIQUE_COMPANY_ID": "c1",
            "UNIQUE_BROWSER_CONFIG": str(config_path),
        },
    ):
        result = runner.invoke(
            cli_main, ["browser", "navigate", "--url", "https://example.com"]
        )

    assert result.exit_code == 0
    body = json.loads(mock_post.call_args.kwargs["data"])
    assert body == {"verb": "navigate", "args": {"url": "https://example.com"}}


@patch("unique_sdk.cli.commands.browser.requests.post")
def test_cli_browser_action_exit_one_on_error(
    mock_post: MagicMock, tmp_path: Path
) -> None:
    config_path = tmp_path / ".unique-browser.json"
    _write_browser_config(config_path)
    mock_post.return_value = _mock_response(
        ok=False,
        status_code=424,
        json_body={"error": "browser_not_connected", "message": "no ext"},
    )

    runner = CliRunner()
    with patch.dict(
        "os.environ",
        {
            "UNIQUE_USER_ID": "u1",
            "UNIQUE_COMPANY_ID": "c1",
            "UNIQUE_BROWSER_CONFIG": str(config_path),
        },
    ):
        result = runner.invoke(cli_main, ["browser", "get-dom"])

    assert result.exit_code == 1
    assert json.loads(result.output)["error"] == "browser_not_connected"
